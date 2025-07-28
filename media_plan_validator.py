#!/usr/bin/env python3
"""
Media Plan Validator (Refactored)

Compares JSON campaign briefs with Word document media plans to validate
consistency and accuracy. Tests budget, duration, platforms, objectives,
and creative assets between input briefs and generated plans.
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from docx import Document
from openai import OpenAI
from dotenv import load_dotenv

# Import our utilities
from utils.document_parser import (
    DocumentSectionDetector, CurrencyExtractor, normalize_channel_name
)
from config.validation_config import (
    AI_STRATEGY_PROMPT, TABLE_FIELD_MAPPINGS, 
    DEFAULT_BUDGET_TOLERANCE, DEFAULT_DURATION_TOLERANCE_DAYS
)

# Load environment variables
load_dotenv()


@dataclass
class ValidationResult:
    """Results of a single validation check"""
    check_name: str
    status: str  # "pass", "fail", "warning", "skip"
    details: str
    expected: Any = None
    actual: Any = None


@dataclass
class TestReport:
    """Complete test report for a media plan validation"""
    test_case: str
    json_brief_file: str
    word_doc_file: str
    timestamp: str
    overall_status: str
    checks: List[ValidationResult]
    notes: List[str]


class MediaPlanValidator:
    def __init__(self, openai_client: Optional[OpenAI] = None):
        """Initialize the validator with optional OpenAI client for AI validation"""
        self.openai_client = openai_client or OpenAI()
        self.tolerance = DEFAULT_BUDGET_TOLERANCE
        self.section_detector = DocumentSectionDetector()
        self.currency_extractor = CurrencyExtractor()
        
    def load_json_brief(self, json_path: str) -> Dict[str, Any]:
        """Load and parse JSON campaign brief"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to load JSON brief: {e}")
    
    def load_word_document(self, docx_path: str) -> Document:
        """Load Word document"""
        try:
            return Document(docx_path)
        except Exception as e:
            raise ValueError(f"Failed to load Word document: {e}")
    
    def validate_budget_from_text(self, json_brief: Dict, doc: Document) -> ValidationResult:
        """Alternative budget validation using text extraction"""
        try:
            expected_budget = float(json_brief.get('budget', 0))
            
            # Extract currency amounts from document text
            currency_data = self.currency_extractor.extract_currency_amounts_from_text(doc)
            
            if not currency_data:
                return ValidationResult(
                    "budget_check", 
                    "fail", 
                    "No currency amounts found in document",
                    expected_budget,
                    0
                )
            
            # Filter for likely budget amounts (near objectives/impressions, reasonable size)
            likely_budgets = []
            for item in currency_data:
                # Consider amounts that are:
                # 1. Near objectives or impressions
                # 2. Reasonable budget size (between 100 and expected_budget * 2)
                # 3. Have platform context
                if ((item['near_objective'] or item['near_impressions']) and 
                    100 <= item['amount'] <= expected_budget * 2):
                    likely_budgets.append(item)
            
            # If no likely budgets, use all currency amounts as potential budgets
            if not likely_budgets:
                likely_budgets = [item for item in currency_data if 100 <= item['amount'] <= expected_budget * 2]
            
            if not likely_budgets:
                return ValidationResult(
                    "budget_check", 
                    "warning", 
                    f"Found {len(currency_data)} currency amounts but none appear to be channel budgets",
                    expected_budget,
                    currency_data
                )
            
            # Sum likely budget amounts
            total_found = sum(item['amount'] for item in likely_budgets)
            
            # Check if total matches expected (within tolerance)
            difference = abs(expected_budget - total_found)
            tolerance_amount = expected_budget * self.tolerance
            
            if difference <= tolerance_amount:
                status = "pass"
                details = f"Found {len(likely_budgets)} budget amounts totaling {total_found}, matches within {self.tolerance*100}% tolerance"
            else:
                status = "fail"  
                details = f"Found {len(likely_budgets)} budget amounts totaling {total_found}, difference of {difference:.2f} exceeds {tolerance_amount:.2f} tolerance"
            
            return ValidationResult(
                "budget_check", 
                status, 
                details, 
                expected_budget, 
                {
                    'total': total_found,
                    'budget_amounts': likely_budgets,
                    'all_currency_data': currency_data
                }
            )
            
        except Exception as e:
            return ValidationResult("budget_check", "fail", f"Error validating budget from text: {e}")
    
    def validate_duration(self, json_brief: Dict, start_date: str, end_date: str) -> ValidationResult:
        """Validate campaign duration consistency"""
        try:
            if not start_date or not end_date:
                return ValidationResult(
                    "duration_check", 
                    "warning", 
                    "Could not extract campaign dates from document"
                )
            
            # Parse dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            actual_duration = (end_dt - start_dt).days + 1  # Include both start and end days
            
            expected_duration = int(json_brief.get('campaign_duration_days', 0))
            
            if actual_duration == expected_duration:
                status = "pass"
                details = "Campaign duration matches exactly"
            elif abs(actual_duration - expected_duration) <= DEFAULT_DURATION_TOLERANCE_DAYS:
                status = "pass"
                details = f"Campaign duration matches within {DEFAULT_DURATION_TOLERANCE_DAYS} day tolerance"
            else:
                status = "fail"
                details = f"Duration mismatch: expected {expected_duration} days, got {actual_duration} days"
            
            return ValidationResult("duration_check", status, details, expected_duration, actual_duration)
            
        except Exception as e:
            return ValidationResult("duration_check", "fail", f"Error validating duration: {e}")
    
    def validate_channel_consistency(self, media_plan_data: List[Dict], doc: Document) -> ValidationResult:
        """Validate that channels in plan match channels in strategy explainer"""
        try:
            # Extract channels from both sources
            plan_channels = self._extract_plan_channels(media_plan_data)
            strategy_channels = self.section_detector.extract_strategy_channels(doc)
            
            if not plan_channels:
                return ValidationResult(
                    "channel_consistency_check",
                    "warning",
                    "No channels found in media plan table"
                )
            
            if not strategy_channels:
                return ValidationResult(
                    "channel_consistency_check",
                    "warning", 
                    "No channels found in strategy explainer section"
                )
            
            # Normalize channel names for comparison
            normalized_plan = [normalize_channel_name(ch) for ch in plan_channels]
            normalized_strategy = [normalize_channel_name(ch) for ch in strategy_channels]
            
            # Check for matches and mismatches
            plan_set = set(normalized_plan)
            strategy_set = set(normalized_strategy)
            
            matching_channels = plan_set.intersection(strategy_set)
            missing_in_strategy = plan_set - strategy_set
            missing_in_plan = strategy_set - plan_set
            
            # Build detailed results
            details_parts = []
            
            # Check channel count
            count_match = len(plan_channels) == len(strategy_channels)
            if not count_match:
                details_parts.append(f"Channel count mismatch: {len(plan_channels)} in plan vs {len(strategy_channels)} in strategy")
            
            # Check for missing channels
            if missing_in_strategy:
                details_parts.append(f"Channels in plan but not in strategy: {', '.join(missing_in_strategy)}")
            
            if missing_in_plan:
                details_parts.append(f"Channels in strategy but not in plan: {', '.join(missing_in_plan)}")
            
            # Determine overall status
            if len(matching_channels) == len(plan_set) == len(strategy_set):
                status = "pass"
                details_parts.append(f"All {len(matching_channels)} channels match between plan and strategy")
            else:
                status = "fail"
                if len(matching_channels) > 0:
                    details_parts.append(f"{len(matching_channels)} channels match, but inconsistencies found")
                else:
                    details_parts.append("No matching channels found between plan and strategy")
            
            details = "; ".join(details_parts) if details_parts else "Channel consistency check completed"
            
            return ValidationResult(
                "channel_consistency_check",
                status,
                details,
                {
                    'plan_channels': plan_channels,
                    'strategy_channels': strategy_channels,
                    'normalized_plan': normalized_plan,
                    'normalized_strategy': normalized_strategy
                },
                {
                    'matching': list(matching_channels),
                    'missing_in_strategy': list(missing_in_strategy),
                    'missing_in_plan': list(missing_in_plan)
                }
            )
            
        except Exception as e:
            return ValidationResult("channel_consistency_check", "fail", f"Error validating channel consistency: {e}")
    
    def _extract_plan_channels(self, media_plan_data: List[Dict]) -> List[str]:
        """Extract channel names from media plan table data"""
        plan_channels = []
        platform_fields = TABLE_FIELD_MAPPINGS['platform_fields']
        
        for row in media_plan_data:
            for field in platform_fields:
                if field in row and row[field]:
                    channel_name = row[field].strip().lower()
                    if channel_name and channel_name not in plan_channels:
                        plan_channels.append(channel_name)
                    break
        
        return plan_channels
    
    def validate_creative_assets(self, json_brief: Dict, creative_checklist: List[str]) -> ValidationResult:
        """Validate creative asset consistency between brief and checklist"""
        try:
            creative_assets = json_brief.get('creative_assets', {})
            has_assets = creative_assets.get('has_assets', False)
            description = creative_assets.get('description', '').lower()
            
            if not has_assets:
                if creative_checklist:
                    return ValidationResult(
                        "creative_check", 
                        "warning", 
                        "Brief says no assets but checklist found in plan"
                    )
                else:
                    return ValidationResult(
                        "creative_check", 
                        "pass", 
                        "No assets required and none found in plan"
                    )
            
            if not creative_checklist:
                return ValidationResult(
                    "creative_check", 
                    "warning", 
                    "Assets mentioned in brief but no checklist found in plan"
                )
            
            # Extract asset types from description
            asset_types = []
            if 'image' in description:
                asset_types.append('image')
            if 'video' in description:
                asset_types.append('video')
            if 'banner' in description:
                asset_types.append('banner')
            if 'carousel' in description:
                asset_types.append('carousel')
            
            # Check if checklist covers required asset types
            checklist_text = ' '.join(creative_checklist).lower()
            missing_types = []
            for asset_type in asset_types:
                if asset_type not in checklist_text:
                    missing_types.append(asset_type)
            
            if not missing_types:
                status = "pass"
                details = "All required asset types found in creative checklist"
            else:
                status = "warning"
                details = f"Missing asset types in checklist: {', '.join(missing_types)}"
            
            return ValidationResult(
                "creative_check", 
                status, 
                details, 
                asset_types, 
                creative_checklist
            )
            
        except Exception as e:
            return ValidationResult("creative_check", "fail", f"Error validating creative assets: {e}")
    
    def validate_strategy_with_ai(self, json_brief: Dict, doc: Document) -> ValidationResult:
        """Use GPT-4 to validate strategy alignment with brief"""
        try:
            if not self.openai_client:
                return ValidationResult(
                    "strategy_ai_check", 
                    "skip", 
                    "OpenAI client not available for AI validation"
                )
            
            # Extract strategy text from document
            strategy_text = ""
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text and len(text) > 50:  # Only include substantial paragraphs
                    strategy_text += text + "\n"
            
            if not strategy_text:
                return ValidationResult(
                    "strategy_ai_check", 
                    "warning", 
                    "No substantial strategy text found in document"
                )
            
            # Format the prompt using our template
            prompt = AI_STRATEGY_PROMPT.format(
                business_description=json_brief.get('business', {}).get('description', 'N/A'),
                business_location=json_brief.get('business', {}).get('location', 'N/A'),
                target_market=json_brief.get('target_market', {}),
                objectives=json_brief.get('objectives', {}),
                budget=json_brief.get('budget', 'N/A'),
                platforms=[acc.get('platform') for acc in json_brief.get('social_accounts', [])],
                strategy_text=strategy_text[:2000]  # Limit to avoid token limits
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a digital marketing expert evaluating campaign consistency."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            if ai_response.startswith("CONSISTENT"):
                status = "pass"
            elif ai_response.startswith("PARTIALLY_CONSISTENT"):
                status = "warning"
            else:
                status = "fail"
            
            return ValidationResult("strategy_ai_check", status, ai_response)
            
        except Exception as e:
            return ValidationResult("strategy_ai_check", "fail", f"Error in AI validation: {e}")
    
    def validate_media_plan(self, json_path: str, docx_path: str, include_ai_validation: bool = False) -> TestReport:
        """Run complete validation of media plan against JSON brief"""
        # Load documents
        json_brief = self.load_json_brief(json_path)
        doc = self.load_word_document(docx_path)
        
        # Extract data from Word document
        start_date, end_date = self.section_detector.extract_campaign_dates(doc)
        media_plan_data = self.section_detector.extract_media_plan_table(doc)
        creative_checklist = self.section_detector.extract_creative_checklist(doc)
        
        # Run validation checks
        checks = []
        checks.append(self.validate_budget_from_text(json_brief, doc))
        checks.append(self.validate_duration(json_brief, start_date, end_date))
        checks.append(self.validate_channel_consistency(media_plan_data, doc))
        checks.append(self.validate_creative_assets(json_brief, creative_checklist))
        
        if include_ai_validation:
            checks.append(self.validate_strategy_with_ai(json_brief, doc))
        
        # Determine overall status
        statuses = [check.status for check in checks]
        if "fail" in statuses:
            overall_status = "fail"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "pass"
        
        # Create test report
        report = TestReport(
            test_case=Path(docx_path).stem,
            json_brief_file=Path(json_path).name,
            word_doc_file=Path(docx_path).name,
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            checks=checks,
            notes=[]
        )
        
        return report
    
    def save_report(self, report: TestReport, output_path: str):
        """Save test report to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Validate media plan consistency with JSON brief')
    parser.add_argument('json_brief', help='Path to JSON campaign brief file')
    parser.add_argument('word_doc', help='Path to Word media plan document')
    parser.add_argument('--output', '-o', help='Output path for test report JSON', default='test_report.json')
    parser.add_argument('--ai-validation', action='store_true', help='Include AI-powered strategy validation')
    parser.add_argument('--tolerance', type=float, default=DEFAULT_BUDGET_TOLERANCE, help=f'Budget tolerance percentage (default: {DEFAULT_BUDGET_TOLERANCE})')
    
    args = parser.parse_args()
    
    try:
        # Initialize validator
        validator = MediaPlanValidator()
        validator.tolerance = args.tolerance
        
        # Run validation
        report = validator.validate_media_plan(
            args.json_brief, 
            args.word_doc, 
            include_ai_validation=args.ai_validation
        )
        
        # Save report
        validator.save_report(report, args.output)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"MEDIA PLAN VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"Test Case: {report.test_case}")
        print(f"Overall Status: {report.overall_status.upper()}")
        print(f"Brief: {report.json_brief_file}")
        print(f"Media Plan: {report.word_doc_file}")
        print(f"\nValidation Results:")
        print(f"{'-'*60}")
        
        for check in report.checks:
            status_symbol = {"pass": "✅", "fail": "❌", "warning": "⚠️", "skip": "⏭️"}.get(check.status, "❓")
            print(f"{status_symbol} {check.check_name}: {check.status.upper()}")
            print(f"   {check.details}")
            if check.expected is not None and check.actual is not None:
                print(f"   Expected: {check.expected}")
                print(f"   Actual: {check.actual}")
            print()
        
        print(f"Report saved to: {args.output}")
        
        # Exit with appropriate code
        sys.exit(0 if report.overall_status == "pass" else 1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
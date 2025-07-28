#!/usr/bin/env python3
"""
Digital Media Planner Test Case Generator

Generates realistic JSON test cases for SME digital media planner using OpenAI API.
Uses configuration from testcase_gen_prompt.json to ensure proper structure and constraints.
"""

import json
import time
import argparse
import sys
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TestCaseGenerator:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize the test case generator.
        
        Args:
            api_key: OpenAI API key (if None, expects OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-4)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.config = self._load_config()
        self.generated_cases = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the test case generation configuration."""
        try:
            with open('testcase_gen_prompt.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: testcase_gen_prompt.json not found in current directory")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing testcase_gen_prompt.json: {e}")
            sys.exit(1)
    
    def _create_prompt(self) -> str:
        """Create the prompt for OpenAI API based on configuration."""
        prompt = f"""
{self.config['task']}

Please generate a single, realistic JSON object with the following structure and requirements:

FIELD STRUCTURE:
{json.dumps(self.config['fields'], indent=2)}

REQUIREMENTS:
{chr(10).join('- ' + req for req in self.config['requirements'])}

ADDITIONAL INSTRUCTIONS:
- Make the business type, location, and targeting geographically and culturally consistent
- Use realistic platform URLs that match the selected platform
- Ensure budget and dates are reasonable for the business type
- Make interests relevant to the business and target demographic
- Choose platforms that make sense for the business type and target audience

Return ONLY the JSON object, no additional text or formatting.
"""
        return prompt
    
    def _validate_json_structure(self, data: Dict[str, Any]) -> bool:
        """
        Basic validation to ensure the JSON has required structure.
        
        Args:
            data: Parsed JSON data to validate
            
        Returns:
            bool: True if structure is valid
        """
        required_fields = ['business', 'target_market', 'objectives', 'lead_preference', 
                          'social_accounts', 'creative_assets', 'budget', 'start_date', 
                          'campaign_duration_days']
        
        for field in required_fields:
            if field not in data:
                print(f"Warning: Missing required field: {field}")
                return False
        
        # Validate business structure
        business_fields = ['description', 'location', 'online', 'website']
        for field in business_fields:
            if field not in data.get('business', {}):
                print(f"Warning: Missing business field: {field}")
                return False
        
        # Validate target_market structure
        target_fields = ['regions_included', 'regions_excluded', 'gender', 'age_groups', 'interests']
        for field in target_fields:
            if field not in data.get('target_market', {}):
                print(f"Warning: Missing target_market field: {field}")
                return False
        
        # Validate social_accounts structure
        if not isinstance(data.get('social_accounts'), list) or len(data['social_accounts']) == 0:
            print("Warning: social_accounts must be a non-empty list")
            return False
        
        for account in data['social_accounts']:
            if 'platform' not in account or 'urls' not in account:
                print("Warning: social_accounts items must have 'platform' and 'urls'")
                return False
        
        return True
    
    def generate_single_testcase(self, retry_count: int = 3) -> Optional[Dict[str, Any]]:
        """
        Generate a single test case using OpenAI API.
        
        Args:
            retry_count: Number of retries for failed API calls
            
        Returns:
            Dict containing the generated test case, or None if failed
        """
        prompt = self._create_prompt()
        
        for attempt in range(retry_count):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that generates realistic test data for digital marketing campaigns. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,  # Add some randomness for variety
                    max_tokens=1500
                )
                
                content = response.choices[0].message.content.strip()
                
                # Try to parse the JSON
                try:
                    test_case = json.loads(content)
                    
                    # Validate structure
                    if self._validate_json_structure(test_case):
                        return test_case
                    else:
                        print(f"Attempt {attempt + 1}: Generated JSON failed validation")
                        
                except json.JSONDecodeError as e:
                    print(f"Attempt {attempt + 1}: Invalid JSON generated: {e}")
                    
            except Exception as e:
                print(f"Attempt {attempt + 1}: API call failed: {e}")
            
            if attempt < retry_count - 1:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
        
        print(f"Failed to generate valid test case after {retry_count} attempts")
        return None
    
    def generate_testcases(self, n: int, delay: float = 1.0) -> List[Dict[str, Any]]:
        """
        Generate n test cases.
        
        Args:
            n: Number of test cases to generate
            delay: Delay between API calls in seconds
            
        Returns:
            List of generated test cases
        """
        print(f"Generating {n} test cases...")
        self.generated_cases = []
        
        for i in range(n):
            print(f"Generating test case {i + 1}/{n}...")
            
            test_case = self.generate_single_testcase()
            if test_case:
                self.generated_cases.append(test_case)
                print(f"✓ Test case {i + 1} generated successfully")
            else:
                print(f"✗ Failed to generate test case {i + 1}")
            
            # Add delay between calls (except for the last one)
            if i < n - 1 and delay > 0:
                time.sleep(delay)
        
        print(f"\nGeneration complete: {len(self.generated_cases)}/{n} test cases generated")
        return self.generated_cases
    
    def save_to_file(self, filename: str = "testcases_output.json"):
        """Save generated test cases to a JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.generated_cases, f, indent=2, ensure_ascii=False)
            print(f"Test cases saved to {filename}")
        except Exception as e:
            print(f"Error saving to file: {e}")
    
    def print_results(self):
        """Print generated test cases to terminal with nice formatting."""
        if not self.generated_cases:
            print("No test cases to display")
            return
        
        print("\n" + "="*80)
        print("GENERATED TEST CASES")
        print("="*80)
        
        for i, case in enumerate(self.generated_cases, 1):
            print(f"\nTest Case {i}:")
            print("-" * 40)
            print(json.dumps(case, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Generate realistic JSON test cases for SME digital media planner')
    parser.add_argument('n', type=int, help='Number of test cases to generate')
    parser.add_argument('--model', default='gpt-4', help='OpenAI model to use (default: gpt-4)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--output', default='testcases_output.json', help='Output filename (default: testcases_output.json)')
    
    args = parser.parse_args()
    
    if args.n <= 0:
        print("Error: Number of test cases must be positive")
        sys.exit(1)
    
    try:
        generator = TestCaseGenerator(model=args.model)
        test_cases = generator.generate_testcases(args.n, delay=args.delay)
        
        if test_cases:
            generator.print_results()
            generator.save_to_file(args.output)
        else:
            print("No test cases were generated successfully")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nGeneration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
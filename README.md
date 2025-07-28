# Media Plan Validator

A validation tool that compares JSON campaign briefs with Word document media plans to check for consistency issues across budgets, timelines, channels, and creative requirements.

## What it does

The validator runs several checks:
- **Budget validation** - Makes sure channel budgets add up to the total budget in your JSON brief
- **Duration check** - Confirms campaign timeline matches between brief and plan
- **Channel consistency** - Verifies that channels in your media plan table match what's explained in the strategy section
- **Creative assets** - Checks if required assets are covered in the creative checklist
- **AI strategy review** - Optional GPT-4 analysis of strategic alignment

## Project Structure

```
├── media_plan_validator.py             # Main validation script
├── generate_testcases.py               # Tool for generating test cases
├── config/
│   └── validation_config.py            # Settings and configuration
├── utils/
│   └── document_parser.py              # Document parsing helpers
├── test_cases/                         # Sample test files
├── prompts/                            # Test case generation prompts
└── requirements.txt                    # Python dependencies
```

## Getting Started

Install the dependencies:
```bash
pip install -r requirements.txt
```

Set up your OpenAI API key in a `.env` file (only needed for AI validation):
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

## Basic Usage

Run a validation:
```bash
python media_plan_validator.py test_cases/test_compare_json_doc.json test_cases/test_compare_json_doc.docx
```

Include AI strategy validation:
```bash
python media_plan_validator.py brief.json plan.docx --ai-validation
```

Save results to a custom file:
```bash
python media_plan_validator.py brief.json plan.docx --output my_report.json
```

## Sample Output

```
============================================================
MEDIA PLAN VALIDATION REPORT
============================================================
Test Case: test_compare_json_doc
Overall Status: PASS
Brief: test_compare_json_doc.json
Media Plan: test_compare_json_doc.docx

Validation Results:
------------------------------------------------------------
✅ budget_check: PASS
   Found 3 budget amounts totaling 5000.0, matches within 5% tolerance

✅ duration_check: PASS
   Campaign duration matches within 1 day tolerance

✅ channel_consistency_check: PASS
   All 4 channels match between plan and strategy

✅ creative_check: PASS
   All required asset types found in creative checklist
```

## Generating Test Cases

You can create realistic test data for validation testing:

```bash
# Generate 5 standard test cases
python generate_testcases.py 5

# Generate Cyprus-specific test cases
python generate_testcases.py 3 --config prompts/testcase_gen_prompt_cyprus.json

# Generate problematic test cases (for testing error handling)
python generate_testcases.py 10 --config prompts/testcase_gen_prompt_bad_data.json
```

## Test with Sample Data

Try the validator with the included test cases:

```bash
# This should pass all validations
python media_plan_validator.py test_cases/test_compare_json_doc.json test_cases/test_compare_json_doc.docx

# This should fail with channel consistency issues
python media_plan_validator.py test_cases/problem_input.json test_cases/problem_input.docx
```

## What Each Check Does

**Budget Validation**
Looks for currency amounts in your Word document (but ignores amounts in the strategy explainer section since those are usually examples). Adds them up and compares to your JSON brief budget. Fails if there's more than a 5% difference.

**Duration Check**
Extracts campaign start and end dates from your document and calculates the duration. Compares this to the `campaign_duration_days` in your JSON brief. Allows for 1 day tolerance.

**Channel Consistency**
Pulls channel names from your media plan table and compares them to channels mentioned in the strategy explainer section (looks for "Channel: Platform Name" format). Fails if there are any mismatches.

**Creative Assets**
Compares the asset description in your JSON brief with what's listed in the creative requirements checklist. Checks for basic asset types like images, videos, banners, and carousels.

**AI Strategy Review**
Sends your brief and strategy text to GPT-4 to evaluate if the strategy makes sense given the business context, target audience, budget, and objectives.

## File Format Requirements

**JSON Brief**
Your JSON file should include business info, target market, objectives, budget, timeline, and creative assets. Check the sample files in `test_cases/` for the expected structure.

**Word Document**
The Word doc should have:
- Campaign start and end dates somewhere in the text
- A table with platform/channel names and budget amounts
- A "Strategy Explainer" section with "Channel: [Platform Name]" labels
- A creative requirements checklist section

## Common Issues

**Budget check fails with "No currency amounts found"**
Make sure your budget amounts appear before the "2. Strategy Explainer" section in your document. The validator skips currency amounts in the strategy section since those are typically examples.

**Channel consistency fails**
Check that your strategy explainer section uses the format "Channel: Platform Name" and that these match the platforms in your media plan table.

**AI validation errors**
Make sure your OpenAI API key is set correctly and has available credits. You can skip AI validation by not using the `--ai-validation` flag.

## Configuration

You can adjust settings like budget tolerance, currency patterns, and AI prompts by editing files in the `config/` folder. The default budget tolerance is 5% and duration tolerance is 1 day.

## Future Features

**Batch Processing** - We're planning to add batch validation for processing multiple JSON/DOCX pairs at once. This will include:
- Auto-detection of file pairs in directories
- Progress tracking and error handling
- Consolidated reporting across multiple campaigns
- Resume capability for large batches

This feature will be built once we have sufficient planner output data once the planner can accept batch inputs.
import argparse
import os
import sys
from pathlib import Path
import importlib.util
import pandas as pd
import traceback
import logging

from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParserAgent:
    def __init__(self,target_bank : str):
        self.target_bank = target_bank
        self.data_dir = Path("data")
        possible_pdf_names = [
            f"{target_bank}_sample.pdf",
            f"{target_bank} sample.pdf",
            f"{target_bank.upper()}_sample.pdf",
            f"{target_bank.upper()} sample.pdf",
            f"{target_bank.lower()}_sample.pdf",
            f"{target_bank.lower()} sample.pdf"
        ]

        self.pdf_path = None
        for pdf_name in possible_pdf_names:
            path = self.data_dir / pdf_name
            if path.exists():
                self.pdf_path = path
                break

        possible_csv_names =[
            f"{target_bank}_expected.csv",
            f"{target_bank}_result.csv",
            f"{target_bank}.csv",
            f"expected_{target_bank}.csv",
            f"result.csv",
            f"expected.csv"
        ]

        self.csv_path = None
        for csv_name in possible_csv_names:
            path = self.data_dir / csv_name
            if path.exists():
                self.csv_path = path
                break

        self.output_parser = Path(f"custom_parser/{target_bank}_parser.py")
        self.max_attempts = 5

        self.agent = Agent(
            model = Gemini(
                id="gemini-2.0-flash",
                top_p=0.1,
                top_k=1,
                ),
            markdown = False,
        )

        self.output_parser.parent.mkdir(exist_ok=True)

        if self.pdf_path:
            logger.info(f"Pdf found : {self.pdf_path}")
        if self.csv_path:
            logger.info(f"Found csv for validation:{self.csv_path}")

        
    def analyze_pdf_structure(self) -> str :
        logger.info(f"Analyzing pdf structure:{self.pdf_path}")

        analysis_prompt = f"""
        You are analyzing a bank statement PDF to understand its structure completely from scratch.
        PDF Path: {self.pdf_path}
        
        Examine the PDF and discover:
        1. What columns exist and their EXACT names as written
        2. What data patterns you see in each column
        3. How dates are formatted in this specific document
        4. How numbers/amounts are formatted 
        5. What currency symbols or indicators are used
        6. How many pages of data exist
        7. Where the actual transaction data starts and ends
        8. Any headers, footers, or summary sections to ignore
        9. How to distinguish transaction rows from other content
        10. Any multi-line entries or special formatting
        
        Be completely objective - describe exactly what you observe without making assumptions.
        Don't assume standard banking column names - tell me what this specific PDF actually contains.
        """

        response = self.agent.run(analysis_prompt)
        analysis = response.content.strip()
        logger.info(f"PDF analysis completed")
        return analysis
    
    def generate_parser_code(self,pdf_analysis: str, attempt: int=1) -> str:
        logger.info(f"Generating parser code (attempt {attempt}/{self.max_attempts})")

        error_feedback = ""
        if hasattr(self,'last_error'):
            error_feedback = f"""

            PREVIOUS ATTEMPT FAILED:
            {self.last_error}
            
            LEARN FROM THIS: Apply specific fixes while keeping the same overall approach.
            """
        
        generation_prompt = f"""
        Create a PDF parser based on the discovered structure below.
        
        DISCOVERED PDF STRUCTURE:
        {pdf_analysis}
        
        TARGET: {self.target_bank}
        ATTEMPT: {attempt}/{self.max_attempts}
        {error_feedback}
        
        Generate: def parse(pdf_path: str) -> pd.DataFrame
        
         
        You are a resilient PDF parsing assistant. Your goal is to generate Python code that extracts tabular data from any PDF without hardcoding column names, types, or structure. Follow these instructions exactly and output only Python code (no markdown, no explanation).
        Be completely intelligent and adaptive. If previous attempts had issues, analyze why and fix them while maintaining full discovery-based approach.
        1. Begin by importing pandas, pdfplumber, re, and PyPDF2.
        2. Open the PDF and inspect every page’s content.
        3. Attempt three extraction strategies in order, falling back only if the previous yields no data:
            - pdfplumber table extraction
            - pdfplumber text extraction with pattern matching
            - PyPDF2 raw text extraction with regex
        4. For each extracted row, strip whitespace and record every unique row in a master list.
        5. Dynamically identify header candidates by frequency across all pages.
        6. Select the most frequent row pattern as the header definition.
        7. Exclude any rows identical to that header from your data rows.
        8. Log, as debug comments in the code, every header candidate and which rows were removed.
        9. Use the discovered header row to name DataFrame columns.
        10.Clean each cell by trimming whitespace, convert numeric-like strings to numbers, and handle missing or empty cells gracefully.
        11.Normalize and enforce deterministic structure:
            - Reset the DataFrame index (drop old labels).
            - CRITICAL: Preserve the original column order as discovered in the header row - DO NOT sort alphabetically or reorder columns
            - Strip whitespace and normalize Unicode (NFC) in all string cells.
            - Normalize missing values to NaN uniformly.
            - Explicitly cast column types based on observed patterns (int, float, datetime).
            - Ensure column names match the header row exactly AND maintain the same sequence as found in the PDF.
            - Optionally, if a reference DataFrame exists, compare with assert_frame_equal(check_dtype=True, check_like=True) and log any diffs
        12.Before returning, validate that:
            - No header rows remain in the data
            - Column count matches the header definition
            - Column order matches the original header sequence from the PDF
            - Data types align with normalized patterns
            - If validation fails, automatically re-run extraction with enhanced debug output and fallback logic
        13. Return the final pandas DataFrame object with columns in the exact order they were discovered.

        SELF-CORRECTION RULES
        - On header mismatch or missing columns, compare actual vs expected and adjust extraction logic.
        - On row count anomalies, debug inclusion/exclusion criteria and reprocess only the affected pages.
        - On parsing errors, add detailed debug comments showing regex patterns and fallback triggers.
        - Always include debug logs as comments showing decisions, removed rows, normalization steps, and final validation results
        - NEVER reorder columns from their natural sequence in the source PDF

        """

        response = self.agent.run(generation_prompt)
        code = response.content.strip()

        if code.startswith('```'):
            code = code.split('\n', 1)[-1]  
        if code.endswith('```'):
            code = code[:-3] 

        code = code.strip()
        return code
    

    def test_parser(self) -> tuple[bool, pd.DataFrame, str]:
        logger.info(f"Testing generated parser")

        try :
            spec = importlib.util.spec_from_file_location(
                f"{self.target_bank}_parser",
                self.output_parser
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            print(f"running parser on :{self.pdf_path}")
            result_df = module.parse(str(self.pdf_path))

            if result_df is None:
                return False , None , "parser returned None"
            if result_df.empty:
                return False , None , "parser returned empty Dataframe"
            
            print(f"Parser structure:")
            print(f"   Shape: {result_df.shape}")
            print(f"   Columns: {list(result_df.columns)}")
            print(f"   Sample data:\n{result_df.head()}")

            logger.info(f"Parser executed sucessfully")
            return True , result_df , "Success"
        
        except Exception as e:
            error_message = f"Parser execution failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            return False , None , error_message
        

    def validate(self , result_df : pd.DataFrame) -> tuple[bool,str]:
        logger.info(f"Validating against expected output")

        try: 
            if not self.csv_path:
                logger.info("No expected csv file found")
                return True , "No validation file available"
            
            expected_df = pd.read_csv(self.csv_path)

            print(f"Comparision:")
            print(f"   Generated: {result_df.shape} with columns {list(result_df.columns)}")
            print(f"   Expected:  {expected_df.shape} with columns {list(expected_df.columns)}")

            if result_df.equals(expected_df):
                return True  , "Validation passed"
            
            else:
                return False, "Data content doesn't match exactly"

            
            
        
        except Exception as e:
            logger.error(f"validation error: {e}")
            return False , f"validation failed: {str(e)}"
        
    def run(self) -> bool:
        logger.info(f"Starting parser generation for {self.target_bank}")

        if not self.pdf_path:
            logger.info(f"No pdf file found for {self.target_bank}")

        ### STEP 1 : analyze pdf 
          
        try:
            pdf_analysis = self.analyze_pdf_structure()
        except Exception as e:
            logger.error(f"Pdf analysis failed: {e}")
            traceback.print_exc()
            return False
        
        ### STEP 2 : parser code generation (plan->generate code -> test -> fix )

        for attempt in range(1,self.max_attempts +1):
            logger.info(f"Attempt {attempt}/{self.max_attempts}")

            try:
                parser_code = self.generate_parser_code(pdf_analysis , attempt)

                if not parser_code or len(parser_code.strip())<50:
                    error_message = "generated parser code is too short"
                    logger.error(f"{error_message}")
                    if attempt < self.max_attempts:
                        self.last_error = error_message
                        continue
                    else:
                        return False
                    
                self.output_parser.write_text(parser_code,encoding='utf-8')
                logger.info(f"Parser saved : {self.output_parser}")

                success , result_df , test_message = self.test_parser()

                if not success:
                    logger.warning(f"Test failed : {test_message}")
                    if attempt < self.max_attempts:
                        self.last_error = test_message
                        continue
                    else:
                        logger.error(f"All discovery attempts failed")
                        return False
                    
                valid , validation_message = self.validate(result_df)
                logger.info(f"Validation: {validation_message}")

                if valid:
                    logger.info(f"Success")

                    output_csv = Path(f"parsed_{self.target_bank}.csv")
                    result_df.to_csv(output_csv, index=False)
                    logger.info(f"Results saved to {output_csv}")

                    return True
                
                else:
                    logger.warning(f"Validation failed: {validation_message}")
                    if attempt < self.max_attempts:
                        self.last_error = validation_message
                        continue
                    else:
                        if result_df.shape[0] > 0:
                            logger.info(f"Partial success on final attempt")
                            output_csv = Path(f"parsed_{self.target_bank}.csv")
                            result_df.to_csv(output_csv,index=False)
                            return True
                        return False
                    
            except Exception as e:
                error_message = f"Attempt {attempt} failed : {str(e)}"
                logger.error(error_message)
                if attempt < self.max_attempts:
                    self.last_error = error_message
                    continue
                else:
                    logger.error(f"All attempts failed")
                    return False
        return False
    

def main():
    parser = argparse.ArgumentParser(
        description='AI agent for generating parser code for the given pdf and converting to csv',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--target', required=True)
    args = parser.parse_args()

    if not os.getenv('GOOGLE_API_KEY'):
        logger.error("API Key not found")
        sys.exit(1)

    try:
        agent = ParserAgent(args.target)
        success = agent.run()

        if success:
            print(f"\n parser for {args.target} completed!")

        else:
            print(f"\n failed for {args.target}")

    except Exception as e:
        logger.error(f"error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 





        









import importlib.util
from pathlib import Path
import pandas as pd

def test_parser_contract():
    
    
    target = "icici"
    
    
    data_dir = Path("data")
    

    possible_pdf_names = [
        f"{target}_sample.pdf",
        f"{target} sample.pdf", 
        f"{target.upper()}_sample.pdf",
        f"{target.upper()} sample.pdf",
        f"{target.lower()}_sample.pdf",
        f"{target.lower()} sample.pdf"
    ]
    
    pdf_path = None
    for pdf_name in possible_pdf_names:
        path = data_dir / pdf_name
        if path.exists():
            pdf_path = path
            break
    

    possible_csv_names = [
        f"{target}_expected.csv",
        f"{target}_result.csv",
        f"{target}.csv",
        f"expected_{target}.csv",
        f"result.csv",
        f"expected.csv"
    ]
    
    csv_path = None
    for csv_name in possible_csv_names:
        path = data_dir / csv_name
        if path.exists():
            csv_path = path
            break
    
    parser_path = Path(f"custom_parser/{target}_parser.py")
    

    assert parser_path.exists(), f"Parser not found: {parser_path}. Run 'python agent.py --target {target}' first"
    assert pdf_path is not None, f"PDF not found. Tried: {possible_pdf_names}"
    assert csv_path is not None, f"Expected CSV not found. Tried: {possible_csv_names}"
    
    ### Loading the generated parser
    spec = importlib.util.spec_from_file_location(f"{target}_parser", parser_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    ### Run parser and compare
    result_df = module.parse(str(pdf_path))
    expected_df = pd.read_csv(csv_path)
    
    assert result_df is not None, "Parser returned None"
    assert not result_df.empty, "Parser returned empty DataFrame"
    assert result_df.equals(expected_df), f"DataFrame mismatch\nGot: {result_df.shape}\nExpected: {expected_df.shape}"

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from synology_api.filestation import FileStation

# Load environment variables
load_dotenv()

# Configuration
class Config:
    CPS_USERNAME = os.getenv("CPS_USERNAME")
    CPS_PASSWORD = os.getenv("CPS_PASSWORD")
    NAS_DOMAIN = os.getenv("NAS_DOMAIN")
    NAS_USERNAME = os.getenv("NAS_USERNAME")
    NAS_PASSWORD = os.getenv("NAS_PASSWORD")
    NAS_PORT = 5001
    DAILY_PATH = os.getenv("DAILY_PATH")
    DOWNLOAD_DIR = "downloads"

def get_synology_connection():
    return FileStation(
        Config.NAS_DOMAIN,
        Config.NAS_PORT,
        Config.NAS_USERNAME,
        Config.NAS_PASSWORD,
        secure=True,
        dsm_version=7
    )

def upload_to_synology(local_path, fl):
    current_path = Config.DAILY_PATH
    
    if not os.path.exists(local_path):
        print(f"Error: Local file '{local_path}' not found.")
        return None

    # Ensure path exists on Synology
    now = datetime.now()
    target_path_parts = [str(now.year), str(now.month), str(now.day)]
    
    print(f"Starting check at base path: {current_path}")
    for part in target_path_parts:
        check = fl.get_file_list(folder_path=current_path)
        if 'data' not in check or 'files' not in check['data']:
            print(f"Failed to list directory {current_path}: {check}")
            return check

        existing_folders = [f['name'] for f in check['data']['files']]
        if part not in existing_folders:
            print(f"Creating folder: {part} inside {current_path}")
            fl.create_folder(folder_path=current_path, name=part)
        
        current_path = f"{current_path}/{part}"

    print(f"Uploading file to: {current_path}")
    
    # Generate timestamped filename to avoid overwrites
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(local_path)
    base, ext = os.path.splitext(filename)
    new_filename = f"{base}_{timestamp}{ext}"
    
    # Rename locally
    directory = os.path.dirname(local_path)
    new_local_path = os.path.join(directory, new_filename)
    
    try:
        os.rename(local_path, new_local_path)
        print(f"Renamed local file to: {new_local_path}")
        
        response = fl.upload_file(dest_path=current_path, file_path=new_local_path)
        print(f"Sync result for {new_local_path}: {response}")
        return response
        
    except Exception as e:
        print(f"error during rename/upload: {e}")
        return None

def login_to_cps(page):
    print("logging in to cps...")
    page.goto("https://maa-admin.onlinepo.com/")
    page.fill("#ASPxPanel2_txtUsername_I", Config.CPS_USERNAME)
    page.fill("#ASPxPanel2_txtPassword_I", Config.CPS_PASSWORD)
    page.click("#ASPxPanel2_btnSignIn_CD")
    page.wait_for_load_state("networkidle")
    print("logged in successfully.")

def download_simple_report(page, url, filename, export_selector=None):
    print(f"navigating to {filename}...")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    
    if export_selector:
        print("opening export menu...")
        page.click(export_selector)
        page.wait_for_load_state("networkidle")

    print(f"downloading {filename}...")
    with page.expect_download() as download_info:
        # if specific export selector was used (TL), we click 'Print to Excel'
        # if regular (RFM), we click 'Export to Excel'
        # based on original script logic:
        if export_selector:
             page.click("text=Print to Excel")
        else:
             page.click("text=Export to Excel")

    download = download_info.value
    path = os.path.join(Config.DOWNLOAD_DIR, filename)
    download.save_as(path)
    print(f"downloaded: {path}")
    return path

def download_po_report(page):
    print("navigating to po entry list...")
    page.goto("https://maa-admin.onlinepo.com/CPS/Forms/Project/BIZ_POEntryList.aspx")
    page.wait_for_load_state("networkidle")

    # change date
    date_selector = "#ctl00_ctl00_ContentPlaceHolder1_ContentPlaceHolder1_ASPxRoundPanel3_menuPrintReq_ITCNT2_dpDateCreated_I"
    page.wait_for_selector(date_selector)
    page.click(date_selector)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.type(date_selector, "01/01/2025") # Hardcoded per user request
    page.keyboard.press("Enter")
    print("date set to 01/01/2025. waiting 10 seconds...")
    page.wait_for_timeout(10000)

    # change status
    status_selector = "#ctl00_ctl00_ContentPlaceHolder1_ContentPlaceHolder1_ASPxRoundPanel3_menuPrintReq_ITCNT0_cboComboStatus_I"
    page.click(status_selector)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.type(status_selector, "All")
    page.keyboard.press("Enter")
    print("status set to All. waiting 30 seconds...")
    page.wait_for_timeout(30000)

    # export
    popout_arrow = "#ctl00_ctl00_ContentPlaceHolder1_ContentPlaceHolder1_ASPxRoundPanel3_menuPrintReq_DXI6_P"
    page.click(popout_arrow)
    
    print("downloading po entry list (60s timeout)...")
    try:
        with page.expect_download(timeout=60000) as download_info:
            page.click("text=Print to Excel", no_wait_after=True)
            print("server generating file...")
        
        download = download_info.value
        path = os.path.join(Config.DOWNLOAD_DIR, "PO Entry List.xlsx")
        download.save_as(path)
        print(f"downloaded: {path}")
        return path
        
    except Exception as e:
        print(f"PO download failed: {e}")
        raise e

def main():
    if not os.path.exists(Config.DOWNLOAD_DIR):
        os.makedirs(Config.DOWNLOAD_DIR)

    files_to_sync = []

    try:
        with sync_playwright() as p:
            # Headless=True for CI/CD, change to False for debugging
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                login_to_cps(page)
                
                # 1. RFM
                rfm_path = download_simple_report(
                    page, 
                    "https://maa-admin.onlinepo.com/CPS/Forms/Project/BIZ_RequisitionEntryList.aspx", 
                    "Requisition Entry List.xlsx"
                )
                files_to_sync.append(rfm_path)
                
                # 2. Transfer List
                tl_path = download_simple_report(
                    page,
                    "https://maa-admin.onlinepo.com/CPS/Forms/Project/BIZ_TransferList.aspx",
                    "Transfer List.xlsx",
                    export_selector="#ctl00_ctl00_ContentPlaceHolder1_ContentPlaceHolder1_ASPxRoundPanel3_mnuNAV_DXI6_PImg"
                )
                files_to_sync.append(tl_path)
                
                # 3. PO Entry List
                po_path = download_po_report(page)
                files_to_sync.append(po_path)
                
            finally:
                browser.close()
                
        # Sync to Synology
        if files_to_sync:
            print("\nStarting Synology Sync...")
            fl = get_synology_connection()
            for file_path in files_to_sync:
                upload_to_synology(file_path, fl)

    except Exception as e:
        print(f"Critical Automation Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import pandas as pd
from playwright.sync_api import Page, expect

def scrape_po_receive_data(page: Page, start_id: int, end_id: int, username: str = "laurentius adi", password: str = "proc") -> pd.DataFrame:
    """
    Scrapes PO Receive Attachment data from maa-m.onlinepo.com.
    Returns the path to the saved CSV file.
    """
    base_url = "https://maa-m.onlinepo.com/POReceiveAttachment.aspx?mode=view&ID={}"
    output_csv = "downloads/po_receive_data.csv"
    
    all_rows = []

    print("Logging in to PO Receive Attachment...")
    # Login
    page.goto(base_url.format(start_id))
    
    # Check if login is needed
    if page.locator("#tbUserName").is_visible():
        page.fill("#tbUserName", username)
        page.fill("#tbPassword", password)
        page.click("#btnLogin")
        page.wait_for_url(lambda url: "Login" not in url)
        print("Logged in successfully.")

    for doc_id in range(start_id, end_id + 1):
        print(f"Processing ID {doc_id}")
        try:
            page.goto(base_url.format(doc_id))            

            req_number_locator = page.locator("#MainContent_txtReqNumber")
            
            frame = page
            if not req_number_locator.is_visible(timeout=5000):
                frames = page.frames
                if len(frames) > 1:
                    # Try the second frame (first is usually main)
                    frame = frames[1] 
                    req_number_locator = frame.locator("#MainContent_txtReqNumber")
            
            req_number_locator.wait_for(state="attached", timeout=10000)
        
            
            req_number = req_number_locator.input_value().strip()
            po_number = frame.locator("#MainContent_txtPONumber").input_value().strip()
            receive_date = frame.locator("#MainContent_txtReceiveDate").input_value().strip()
            receive_by = frame.locator("#MainContent_txtReceiveBy").input_value().strip()
            
            rows = frame.locator("tbody tr").all()
            
            for row in rows:
                cols = row.locator("td").all()
                if len(cols) >= 3:
                    all_rows.append({
                        "ID": doc_id,
                        "ReqNumber": req_number,
                        "PONumber": po_number,
                        "ReceiveDate": receive_date,
                        "ReceiveBy": receive_by,
                        "ItemName": cols[0].inner_text().strip(),
                        "Unit": cols[1].inner_text().strip(),
                        "Quantity": cols[2].inner_text().strip(),
                    })
                    
        except Exception as e:
            print(f"Error processing ID {doc_id}: {e}")
            continue

    # Return DataFrame
    df = pd.DataFrame(all_rows)
    print(f"Scraped {len(df)} rows for PO Receive.")
    return df


def scrape_tl_receive_data(page: Page, start_id: int, end_id: int, username: str = "laurentius adi", password: str = "proc") -> pd.DataFrame:
    """
    Scrapes PO Receive Attachment data from maa-m.onlinepo.com.
    Returns the path to the saved CSV file.
    """
    base_url = "https://maa-m.onlinepo.com/ReceiveTransferItemDetail.aspx?ID={}"
    output_csv = "downloads/tl_receive_data.csv"
    
    all_rows = []

    print("Logging in to TL Receive Attachment...")
    # Login
    page.goto(base_url.format(start_id))

    # Check if login is needed
    if page.locator("#tbUserName").is_visible():
        page.fill("#tbUserName", username)
        page.fill("#tbPassword", password)
        page.click("#btnLogin")
        page.wait_for_url(lambda url: "Login" not in url)
        print("Logged in successfully.")

    for doc_id in range(start_id, end_id + 1):
        print(f"Processing ID {doc_id}")
        try:
            page.goto(base_url.format(doc_id))            

            tr_number_locator = page.locator("#MainContent_txtTransferNumber")
                
            frame = page
            if not tr_number_locator.is_visible(timeout=5000):
                frames = page.frames
                if len(frames) > 1:
                    # Try the second frame (first is usually main)
                    frame = frames[1] 

            tr_number_locator.wait_for(state="attached", timeout=10000)
    
         
            transfer_number = frame.locator("#MainContent_txtTransferNumber").input_value().strip()
            receive_date = frame.locator("#MainContent_txtReceiveDate").input_value().strip()
            receive_by = frame.locator("#MainContent_txtReceiveBy").input_value().strip()
            
            rows = frame.locator("tbody tr").all()

            for row in rows:
                cols = row.locator("td").all()
                if len(cols) >= 3:
                    all_rows.append({
                        "ID": doc_id,
                        "TransferNumber": transfer_number,
                        "ReceiveDate": receive_date,
                        "ReceiveBy": receive_by,
                        "ItemName": cols[0].inner_text().strip(),
                        "Unit": cols[1].inner_text().strip(),
                        "Quantity": cols[2].inner_text().strip(),
                    })


        except Exception as e:
            print(f"Error processing ID {doc_id}: {e}")
            continue
        
    # Return DataFrame
    df = pd.DataFrame(all_rows)
    print(f"Scraped {len(df)} rows for TL Receive.")
    return df



from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


def scrape_inventory_handover(
    page: Page,
    start_id: int,
    end_id: int,
    username: str = "laurentius adi",
    password: str = "proc"
) -> pd.DataFrame:
    """
    Scrapes Inventory Handover data from maa-m.onlinepo.com
    Returns a pandas DataFrame.
    """

    base_url = "https://maa-m.onlinepo.com/InventoryHandoverDetail.aspx?id={}"
    all_rows = []

    print("Logging in to Inventory Handover system...")
    page.goto(base_url.format(start_id), wait_until="load")

    # ---------- LOGIN (ONLY IF REQUIRED) ----------
    if page.locator("#tbUserName").is_visible():
        page.fill("#tbUserName", username)
        page.fill("#tbPassword", password)
        page.click("#btnLogin")
        page.wait_for_url(lambda url: "Login" not in url)
        print("Logged in successfully.")

    # ---------- ITERATE IDS ----------
    for doc_id in range(start_id, end_id + 1):
        print(f"Processing ID {doc_id}")

        try:
            page.goto(base_url.format(doc_id), wait_until="load")
            page.wait_for_timeout(1500)  # allow JS + iframe init

            # ---------- FIND CORRECT FRAME ----------
            frame = page.main_frame
            for f in page.frames:
                if f.locator("#MainContent_Label2").count() > 0:
                    frame = f
                    break

            # ---------- PAGE MARKER ----------
            frame.locator("#MainContent_Label2").wait_for(timeout=10000)

            # ---------- HEADER ----------
            handover_date = frame.locator(
                "#MainContent_txtDate"
            ).input_value().strip()

            created_by = frame.locator(
                "#MainContent_txtCreatedBy"
            ).input_value().strip()

            # ---------- ITEM TABLE ----------
            rows = frame.locator("tbody tr").all()
            if not rows:
                continue

            for row in rows:
                cols = row.locator("td").all()
                if len(cols) != 3:
                    continue

                # Column 0
                item_name = cols[0].locator("b").inner_text().strip()
                unit = cols[0].inner_text().split("Unit :")[-1].strip()

                # Column 1
                info = cols[1].inner_text().split("\n")
                po_number = info[0].replace("PO Number :", "").strip()
                req_number = info[1].replace("Req Number :", "").strip()
                warehouse = info[2].replace("Warehouse :", "").strip()

                # Column 2
                quantity = cols[2].inner_text().strip()

                all_rows.append({
                    "ID": doc_id,
                    "HandoverDate": handover_date,
                    "CreatedBy": created_by,
                    "ItemName": item_name,
                    "Unit": unit,
                    "PONumber": po_number,
                    "ReqNumber": req_number,
                    "Warehouse": warehouse,
                    "Quantity": quantity,
                })

        except PlaywrightTimeoutError:
            print(f"⚠️ Timeout processing ID {doc_id}")
            continue
        except Exception as e:
            print(f"❌ Error processing ID {doc_id}: {e}")
            continue

    df = pd.DataFrame(all_rows)
    print(f"Scraped {len(df)} inventory handover rows.")
    return df

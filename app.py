import streamlit as st
import pdfplumber
import fitz
import tempfile
import pandas as pd
import io
from PIL import Image
import json
import re
import os
from openai import AzureOpenAI

client = AzureOpenAI(
  api_key="c18c9011aa0746d78cd93f07da587452",
  api_version="2024-02-01",
  azure_endpoint="https://gpt4o-adya.openai.azure.com/"
)

# PDF extraction functions
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def extract_images_from_pdf(pdf_file, output_folder):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    image_paths = []
    
    # Process each page for images
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        images = page.get_images(full=True)
        
        for i, img in enumerate(images):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Save image to the output folder
            image_path = f"{output_folder}/page_{page_num+1}_img_{i+1}.png"
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            image_paths.append(image_path)

    pdf_document.close()
    return image_paths


# Streamlit App layout
st.set_page_config(page_title="Catalog PDF Extractor", layout="wide")

# Custom header layout with logo and title
logo_path = "Adya1.png"  # Replace with the path to your logo
logo = Image.open(logo_path)

# Header styling
col1, col2 = st.columns([1, 5])
with col1:
    st.image(logo, use_column_width=True)
with col2:
    st.markdown(
        "<h1 style='text-align: center; color: #2A9D8F;'>PDF to Catalog Extractor</h1>"
        "<hr style='border: none; height: 3px; background-color: #2A9D8F; margin-top: -10px;'>",
        unsafe_allow_html=True
    )

# File uploader
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file:
    if st.button("Submit"):
        if uploaded_file is not None:
    # Create a temporary directory for storing images
            image_path_link=[]
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract images from the PDF
                image_paths = extract_images_from_pdf(uploaded_file, temp_dir)
                
                # Display and provide download links for each image
                for image_path in image_paths:
                    image_path_link.append(image_path)
                pdf_text = extract_text_from_pdf(uploaded_file)
                for img in image_path_link:
                     pdf_text += f"\nImage Link: {img}"
        
        def mock_openai_process(pdf_text):
            messages = [
                {"role": "system", "content": "You are an expert AI assistant."},
                {"role": "user", "content": f"""
            You are an expert AI assistant. I have a list of product details extracted from a catalog in a PDF format. 
            Please process this data and return it in JSON format with the following keys, interpreting terms from the PDF based on their meanings. 
            For example, if the PDF contains "Item Name," interpret it as "Product Name," and if it mentions "Price," interpret it as "MRP."
            Where information is missing, use 'None'. If certain fields like "Address" appear only once in the PDF, apply them to all product entries as necessary.
            Ensure "Time to Ship" is in the format "X D" (e.g., "2D").  only Json . Here are the target JSON keys with their meanings:

            1. "Product Name": The item name.
            2. "Parent SKU Id": Primary SKU identifier for grouped items.
            3. "SKU Id": Unique Stock Keeping Unit identifier.
            4. "HSN Reference Code": Harmonized System of Nomenclature code.
            5. "Short Description": Brief overview or main features.
            6. "Long Description": Extended description.
            7. "Front View": URL or file reference for front view image.
            8. "Left Side View": Left side View image of the product.
            9. "Right Side View": Right side image of the product.
            10. "Top View": Top view image.
            11. "Back View": Back view image.
            12. "Bottom View": Bottom view image.
            13. "MRP": Maximum Retail Price, also called "Price."
            14. "Sales Price": Discounted or sale price.
            15. "Payment Method": Accepted modes of payment.
            16. "UOM type": Unit of Measure type (e.g., "kg").
            17. "UOM value": Quantity in specified unit of measure.
            18. "Location": The physical or virtual place where the product is stored or available.
            19. "Available Quantity Count": The total quantity of a product that is currently available for sale or use in inventory.
            20. "Minimum Alert Quantity Count": The threshold quantity that triggers an alert when the product stock falls below this level, prompting a reorder.
            21. "Package Length (cm)": Length in centimeters.
            22. "Package Width (cm)": Width in centimeters.
            23. "Package Height (cm)": Height in centimeters.
            24. "Package Weight (gm)": Weight in grams.
            25. "Volumetric Weight (gm)": Calculated as (Length * Width * Height) / 5000.
            26. "Package Cost": Cost of packaging.
            27. "Refund Available": Refund policy.
            28. "Cancel Available": Cancellation policy.
            29. "Return Time": Return eligibility duration.
            30. "Seller Return Pickup Available": Seller's pickup policy.
            31. "Time to Ship": Days for dispatch.
            32. "Expected Delivery Time": Delivery duration.
            33. "Expected Delivery Charge": Delivery fee.
            34. "Name": Customer contact name.
            35. "Consumer Care Email": Customer service email.
            36. "Mobile Number": Customer service phone.
            37. "Manufacturer Name": Manufacturer's name.
            38. "Address": Manufacturer or seller’s address.
            39. "Generic Name": Product Name.
            40. "Net Quantity or Measure of Commodity in pkg": Net quantity.
            41. "Month year of manufacture packing import": Manufacturing or packing date.
            42. "Country of Origin": Production country.

            Here is the extracted text:
            {pdf_text}
            """}
            ]
            response = client.chat.completions.create(
                model="gpt4o_deployment",
                messages=messages,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            result=response.choices[0].message.content
            print(result)
            try:
                final_result = json.loads(result)
            except:
                
                pattern = r"```(.*?)```"

                matches = re.findall(pattern, result, re.DOTALL)

                for match in matches:
                    res=match.strip()
                final=res.replace('json','')
                final_result = json.loads(final)

                
            return final_result

        # Process PDF text to JSON
        json_result = mock_openai_process(pdf_text)

        # Convert JSON to DataFrame
        try:
            df = pd.DataFrame(json_result)
        except:
            final_result = [json_result]
            df = pd.DataFrame(final_result)

        # Specified columns for the Excel file
        columns_to_include = [
            "Product Name", "Parent SKU Id", "SKU Id", "HSN Reference Code",
            "Short Description", "Long Description", "Front View", "Left Side View",
            "Right Side View", "Top View", "Back View", "Bottom View", "MRP",
            "Sales Price", "Payment Method", "UOM type", "UOM value", "Location",
            "Available Quantity Count", "Minimum Alert Quantity Count",
            "Package Length (cm)", "Package Width (cm)", "Package Height (cm)",
            "Package Weight (gm)", "Volumetric Weight (gm)", "Package Cost",
            "Refund Available", "Cancel Available", "Return Time",
            "Seller Return Pickup Available", "Time to Ship",
            "Expected Delivery Time", "Expected Delivery Charge", "Name",
            "Consumer Care Email", "Mobile Number", "Manufacturer Name",
            "Address", "Generic Name", "Net Quantity or Measure of Commodity in pkg",
            "Month year of manufacture packing import", "Country of Origin"
        ]

        # Filter DataFrame for columns specified
        df_filtered = df.reindex(columns=columns_to_include)

        # Display result table
        st.write("Extracted Data")
        st.dataframe(df_filtered)

        # Download button for Excel
        excel_data = io.BytesIO()
        df_filtered.to_excel(excel_data, index=False, columns=columns_to_include, engine='xlsxwriter')
        excel_data.seek(0)

        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="catalog_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

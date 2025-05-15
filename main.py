import base64
import os
import streamlit as st
from google import genai
from google.genai import types
from google.genai.types import HarmBlockThreshold
from PIL import Image
from io import BytesIO
import tempfile
from dotenv import load_dotenv
import warnings
import io
import requests

load_dotenv()

def swap_clothing(person_image, clothing_image):
    warning_buffer = io.StringIO()
    warnings.filterwarnings('always')
    
    temp_files = []
    uploaded_files = []
    client = None
    output_image_pil = None
    output_text = ""
    
    with warnings.catch_warnings(record=True) as warning_list:
        try:
            if person_image is None or clothing_image is None:
                return None, "Please upload both images for processing."
            
            api_key = "AIzaSyDfUIz__mxR4s8totMB18TnP2lDdYy2ZCc"
            if not api_key:
                return None, "API Key not configured."
            
            client = genai.Client(api_key=api_key)
            
            for img, prefix in [(person_image, "person"), (clothing_image, "clothing")]:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    img.save(temp_file.name, format="JPEG")
                    temp_files.append(temp_file.name)
            
            uploaded_files = [
                client.files.upload(file=temp_files[0]),
                client.files.upload(file=temp_files[1]),
            ]
            
            prompt = '''
                Edit the person's clothing by swapping it with the clothing in the clothing image.
                Retain the same face, facial features, pose and background from the person image.
                The output image should be an image of the person wearing the clothing from the clothing image with the style of clothing image.
                The image pose and background should be the same as the person image but with the new clothing:
            '''
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="This is the person image. Do not change the face or features of the person. Pay attention and retain the face, environment, background, pose, facial features."),
                        types.Part.from_uri(
                            file_uri=uploaded_files[0].uri,
                            mime_type=uploaded_files[0].mime_type,
                        ),
                        types.Part.from_text(text="This is the clothing image. Swap the clothing onto the person image."),
                        types.Part.from_uri(
                            file_uri=uploaded_files[1].uri,
                            mime_type=uploaded_files[1].mime_type,
                        ),
                        types.Part.from_text(text=prompt),
                        types.Part.from_uri(
                            file_uri=uploaded_files[0].uri,
                            mime_type=uploaded_files[0].mime_type,
                        ),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.099,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
                response_modalities=[
                    "image",
                    "text",
                ],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold=HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
                response_mime_type="text/plain",
            )

            response = client.models.generate_content(
                model="models/gemini-2.0-flash-exp",
                contents=contents,
                config=generate_content_config,
            )
            
            if warning_list:
                output_text += "\nWarnings:\n"
                for warning in warning_list:
                    output_text += f"- {warning.message}\n"
            
            if response and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if part.text is not None:
                            output_text += part.text + "\n"
                        elif part.inline_data is not None:
                            try:
                                if isinstance(part.inline_data.data, bytes):
                                    image_data = part.inline_data.data
                                else:
                                    image_data = base64.b64decode(part.inline_data.data)
                                
                                temp_file_path_output = None 
                                try:
                                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_f:
                                        temp_f.write(image_data)
                                        temp_file_path_output = temp_f.name
                                    
                                    if temp_file_path_output and os.path.exists(temp_file_path_output):
                                        pil_img_from_file = Image.open(temp_file_path_output)
                                        output_image_pil = pil_img_from_file.copy()
                                        pil_img_from_file.close()
                                    else:
                                        output_text += "Internal error: Temporary output image file was not created or found after attempt.\n"
                                        output_image_pil = None
                                
                                except Exception as file_op_error:
                                    output_text += f"Error during temporary image file handling: {str(file_op_error)}\n"
                                    output_image_pil = None
                                finally:
                                    if temp_file_path_output and os.path.exists(temp_file_path_output):
                                        try:
                                            os.unlink(temp_file_path_output)
                                        except Exception as unlink_error: 
                                            output_text += f"Warning: Failed to delete temporary output file {temp_file_path_output}: {str(unlink_error)}\n"
                                
                            except Exception as img_data_error:
                                output_text += f"Error processing image data from API: {str(img_data_error)}\n"
                                output_image_pil = None
            else:
                output_text = "The model did not generate a valid response. Please try again with different images."
        
        except Exception as e:
            error_details = f"Error: {str(e)}\n\nType: {type(e).__name__}"
            if warning_list:
                error_details += "\n\nWarnings:\n"
                for warning in warning_list:
                    error_details += f"- {warning.message}\n"
            print(f"Exception occurred: {error_details}")
            return None, error_details
        
        finally:
            for temp_file_path_to_delete in temp_files:
                if os.path.exists(temp_file_path_to_delete):
                    os.unlink(temp_file_path_to_delete)
            
            for uploaded_file in uploaded_files:
                try:
                    if hasattr(client.files, 'delete') and uploaded_file:
                        client.files.delete(uploaded_file.uri)
                except:
                    pass
            
            client = None
        
        return output_image_pil, output_text

def main():
    st.set_page_config(layout="wide", page_title="Virtual Clothing Try-On")
    st.title("Virtual Clothing Try-On")
    st.markdown("Upload a photo of your model, then choose a predefined outfit or upload your own!")

    person_image_file = st.file_uploader("Upload Model Image", type=["jpg", "jpeg", "png"], key="model_img_uploader")

    st.subheader("Choose an outfit:")
    garment_examples = [
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/1.jpg", "Brown Dress"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/2.jpg", "Blue Top"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/3.jpg", "Black Top"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/4.jpg", "Blue T-Shirt"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/5.jpg", "White T-Shirt"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/6.jpg", "Black Crop Top"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/7.jpg", "Black Hoodie"),
        ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/8.jpg", "Beige Shirt"),
    ]

    if 'selected_garment_url' not in st.session_state:
        st.session_state.selected_garment_url = None
    if 'selected_garment_desc' not in st.session_state:
        st.session_state.selected_garment_desc = None

    num_items_per_row = 4
    for i in range(0, len(garment_examples), num_items_per_row):
        row_examples = garment_examples[i:i + num_items_per_row]
        cols = st.columns(len(row_examples))
        for idx_in_row, (url, desc) in enumerate(row_examples):
            original_item_index = i + idx_in_row
            with cols[idx_in_row]:
                if st.button(desc, key=f"garment_btn_{original_item_index}"):
                    st.session_state.selected_garment_url = url
                    st.session_state.selected_garment_desc = desc
                st.image(url, caption=desc, width=100)
    
    if st.session_state.selected_garment_url:
        st.success(f"Selected predefined outfit: {st.session_state.selected_garment_desc}")

    st.subheader("Or upload your own outfit image:")
    custom_clothing_file = st.file_uploader("Upload Outfit Image", type=["jpg", "jpeg", "png"], key="custom_clothing_uploader")
    if custom_clothing_file:
        st.info("Custom outfit uploaded. This will be used if 'Try On' is clicked.")
        st.session_state.selected_garment_url = None 
        st.session_state.selected_garment_desc = None

    if st.button("Try On", key="try_on_submit_button"):
        person_pil_image = None
        clothing_pil_image = None
        error_message = None

        if person_image_file:
            person_pil_image = Image.open(person_image_file).convert("RGB")
        else:
            error_message = "Please upload a Model Image first."
            st.error(error_message)

        if not error_message:
            if custom_clothing_file:
                clothing_pil_image = Image.open(custom_clothing_file).convert("RGB")
            elif st.session_state.selected_garment_url:
                try:
                    response = requests.get(st.session_state.selected_garment_url)
                    response.raise_for_status()
                    clothing_pil_image = Image.open(BytesIO(response.content)).convert("RGB")
                except requests.exceptions.RequestException as e_req:
                    error_message = f"Error fetching predefined outfit '{st.session_state.selected_garment_desc}': {e_req}"
                    st.error(error_message)
                except Exception as e_pil:
                    error_message = f"Error processing predefined outfit image '{st.session_state.selected_garment_desc}': {e_pil}"
                    st.error(error_message)
            else:
                error_message = "Please choose a predefined outfit or upload your own outfit image."
                st.error(error_message)
        
        if not error_message and person_pil_image and clothing_pil_image:
            with st.spinner("Generating your virtual try-on..."):
                output_pil_image, output_text_message = swap_clothing(person_pil_image, clothing_pil_image)
            
            st.subheader("Result")
            if output_pil_image:
                st.image(output_pil_image, caption="Generated Image", use_column_width=True)
            
            if output_text_message and output_text_message.strip():
                if output_pil_image is None:
                    st.error(output_text_message)
                else:
                    st.text_area("Response Details", value=output_text_message, height=100, key="response_details_area")
            elif output_pil_image is None and (not output_text_message or not output_text_message.strip()):
                 st.error("Processing failed and no specific message was returned. Please check image compatibility or try again.")

    else:
        if 'try_on_submit_button' not in st.session_state or not st.session_state.try_on_submit_button:
             st.info("After uploading images, click 'Try On' to see the result here.")

if __name__ == "__main__":
    main()
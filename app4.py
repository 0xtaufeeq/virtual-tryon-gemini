import streamlit as st
from gradio_client import Client, handle_file
import tempfile
from PIL import Image
import requests
from io import BytesIO
import os # Import the os module
# import time # Not needed for the new API

# New API client
client = Client("mr-dee/virtual-try-on")

st.title("Virtual Try-On (mr-dee/virtual-try-on)")

# Upload model image (person_image for the new API)
person_image_file = st.file_uploader("Upload Model Image", type=["png", "jpg", "jpeg"], key="person_img_uploader")

# Predefined garment examples (clothing_image for the new API)
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

st.subheader("Choose an outfit:")
if 'selected_garment_info' not in st.session_state:
    st.session_state.selected_garment_info = None # Stores (url, desc)

cols_garment = st.columns(len(garment_examples))
for idx, (url, desc) in enumerate(garment_examples): # Removed category as it's not used by the new API
    with cols_garment[idx]:
        if st.button(desc, key=f"garment_btn_{idx}"):
            st.session_state.selected_garment_info = (url, desc)
        try:
            img_response = requests.get(url, timeout=5)
            img_response.raise_for_status()
            example_img = Image.open(BytesIO(img_response.content))
            st.image(example_img, caption=desc, use_column_width=True)
        except requests.exceptions.RequestException:
            st.caption(f"Could not load {desc}: Error")
        except IOError:
            st.caption(f"Could not display {desc}")

# Display currently selected predefined garment
if st.session_state.selected_garment_info:
    st.write(f"Selected predefined garment: {st.session_state.selected_garment_info[1]}")

# Upload custom garment image (clothing_image for the new API)
st.subheader("Or upload your own outfit image:")
custom_garment_file = st.file_uploader("Upload Outfit Image", type=["png", "jpg", "jpeg"], key="custom_garment_uploader")

# Button to submit
if st.button("Try On", key="try_on_button"):
    person_image_path = None
    clothing_image_path = None

    if person_image_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=person_image_file.name.split('.')[-1]) as temp_person_img:
            temp_person_img.write(person_image_file.getvalue())
            person_image_path = temp_person_img.name
    else:
        st.error("Please upload a Model Image.")

    if custom_garment_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=custom_garment_file.name.split('.')[-1]) as temp_custom_garment:
            temp_custom_garment.write(custom_garment_file.getvalue())
            clothing_image_path = temp_custom_garment.name
        st.session_state.selected_garment_info = None # Clear predefined selection
    elif st.session_state.selected_garment_info:
        try:
            garment_url, _ = st.session_state.selected_garment_info
            response = requests.get(garment_url)
            response.raise_for_status()
            # Determine suffix from URL or default
            suffix = garment_url.split('.')[-1] if '.' in garment_url.split('/')[-1] else 'jpg'
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as temp_predefined_garment:
                temp_predefined_garment.write(response.content)
                clothing_image_path = temp_predefined_garment.name
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to download selected garment: {e}")
        except Exception as e:
            st.error(f"An error occurred with the selected garment: {e}")
    else:
        if person_image_file:
             st.error("Please choose a predefined outfit or upload your own outfit image.")


    if person_image_path and clothing_image_path:
        with st.spinner("Processing with mr-dee/virtual-try-on API..."):
            try:
                result = client.predict(
                    person_image=handle_file(person_image_path),
                    clothing_image=handle_file(clothing_image_path),
                    api_name="/swap_clothing"
                )
                
                # The API returns a tuple: (image_dict, text_response)
                # The image_dict contains a 'path' to the generated image
                output_image_path = result[0].get('path') if isinstance(result[0], dict) else None
                api_text_response = result[1] if len(result) > 1 else "No text response from API."

                if output_image_path:
                    st.image(output_image_path, caption="Try-On Result")
                else:
                    st.error("API did not return an image path.")
                
                st.text_area("API Text Response:", api_text_response, height=100)

            except Exception as e:
                st.error(f"An API error occurred: {str(e)}")
            finally:
                # Clean up temporary files
                if person_image_path and os.path.exists(person_image_path):
                    os.remove(person_image_path)
                if clothing_image_path and os.path.exists(clothing_image_path):
                    os.remove(clothing_image_path)

    elif not person_image_file:
        pass # Error already shown
    elif not (custom_garment_file or st.session_state.selected_garment_info):
        pass # Error already shown 
import streamlit as st
from gradio_client import Client, handle_file
import tempfile
from PIL import Image
import requests
from io import BytesIO
import time


rate_limit = 1
delay = 1 / rate_limit

client = Client("jallenjia/Change-Clothes-AI")

st.title("Virtual Try-On")

# Upload model image
background_image = st.file_uploader("Upload Model Image", type=["png", "jpg", "jpeg"])

# Predefined garment examples
garment_examples = [
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/1.jpg", "Brown Dress", "dresses"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/2.jpg", "Blue Top", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/3.jpg", "Black Top", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/4.jpg", "Blue T-Shirt", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/5.jpg", "White T-Shirt", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/6.jpg", "Black Crop Top", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/7.jpg", "Black Hoodie", "upper_body"),
    ("https://raw.githubusercontent.com/TaufeeqRiyaz/virtual-try-on-demo/main/8.jpg", "Beige Shirt", "upper_body"),
]

# Display predefined outfit images
st.subheader("Choose an outfit:")

if 'selected_garment' not in st.session_state:
    st.session_state.selected_garment = None

cols = st.columns(len(garment_examples))
for idx, (url, desc, category_val) in enumerate(garment_examples):
    with cols[idx]:
        if st.button(desc, key=f"garment_btn_{idx}"):
            st.session_state.selected_garment = (url, desc, category_val)
        st.image(url, caption=desc, use_column_width=True)

# Debug statement to see the selected garment
st.write("Selected garment:", st.session_state.selected_garment)

# Upload custom garment image
st.subheader("Or upload your own outfit image:")
garment_image = st.file_uploader("Upload Outfit Image", type=["png", "jpg", "jpeg"])
garment_description = st.text_input("Enter Outfit Description") if garment_image else ""
category_options = ["upper_body", "lower_body", "dresses"]
uploaded_garment_category_value = "upper_body"
if garment_image:
    uploaded_garment_category_value = st.selectbox(
        "Select Garment Category for uploaded image",
        category_options,
        index=0,
        key="uploaded_category_selector"
    )

# Button to submit
if st.button("Try On"):
    if background_image is not None and (garment_image or st.session_state.selected_garment):
        with st.spinner("Processing..."):
            try:
                # Save the uploaded model image to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as bg_temp:
                    bg_temp.write(background_image.getbuffer())
                    bg_temp_path = bg_temp.name

                # Determine the garment image, description, and category
                garm_temp_path = None
                current_garment_description = ""
                current_category = "upper_body"

                if garment_image:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as garm_temp_file:
                        garm_temp_file.write(garment_image.getbuffer())
                        garm_temp_path = garm_temp_file.name
                    current_garment_description = garment_description
                    current_category = uploaded_garment_category_value
                elif st.session_state.selected_garment:
                    garment_url, current_garment_description, current_category = st.session_state.selected_garment
                    response = requests.get(garment_url)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as garm_temp_file:
                        garm_temp_file.write(response.content)
                        garm_temp_path = garm_temp_file.name
                
                if not garm_temp_path:
                    st.error("Failed to process garment image.")
                    st.stop()

                # Prepare input data for the API call
                input_dict = {
                    "background": handle_file(bg_temp_path),
                    "layers": [],
                    "composite": None
                }

                # Introduce a delay to prevent rate limiting
                time.sleep(delay)

                # Call the API
                result = client.predict(
                    dict=input_dict,
                    garm_img=handle_file(garm_temp_path),
                    garment_des=current_garment_description,
                    is_checked=True,
                    is_checked_crop=False,
                    denoise_steps=30,
                    seed=-1,
                    category=current_category,
                    api_name="/tryon"
                )

                # Display results
                st.image(result[0], caption="Output Image")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.error("Please upload a model image and choose or upload an outfit image.")
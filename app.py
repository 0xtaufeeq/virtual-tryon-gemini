import streamlit as st
from gradio_client import Client, file
import tempfile

client = Client("Nymbo/Virtual-Try-On", 60.0)

st.title("Virtual Try-On")

background_image = st.file_uploader("Upload Model Image", type=["png", "jpg", "jpeg"])

# Upload garment image
garment_image = st.file_uploader("Upload Outfit Image", type=["png", "jpg", "jpeg"])

# Garment description
garment_description = st.text_input("Enter Outfit Description")

# Checkbox for is_checked
is_checked = True

# Checkbox for is_checked_crop
is_checked_crop = False

# Denoising steps
denoise_steps = 30

# Seed
seed = 42

# Button to submit
if st.button("Try On"):
    if background_image is not None and garment_image is not None and garment_description:
        with st.spinner("Processing..."):
            try:
                # Save the uploaded files to temporary locations
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as bg_temp:
                    bg_temp.write(background_image.getbuffer())
                    bg_temp_path = bg_temp.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as garm_temp:
                    garm_temp.write(garment_image.getbuffer())
                    garm_temp_path = garm_temp.name

                # Prepare input data for the API call
                input_dict = {
                    "background": file(bg_temp_path),
                    "layers": [],
                    "composite": None
                }
                
                # Call the API
                result = client.predict(
                    dict=input_dict,
                    garm_img=file(garm_temp_path),
                    garment_des=garment_description,
                    is_checked=is_checked,
                    is_checked_crop=is_checked_crop,
                    denoise_steps=denoise_steps,
                    seed=seed,
                    api_name="/tryon"
                )

                # Display results
                st.image(result[0], caption="Output Image")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.error("Please upload both images and enter a garment description.")

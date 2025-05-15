import streamlit as st
import requests
from PIL import Image
from io import BytesIO

# API details - ensure your RapidAPI key is correctly set up
RAPIDAPI_URL = "https://try-on-diffusion.p.rapidapi.com/try-on-file"
RAPIDAPI_HEADERS = {
	"x-rapidapi-key": "828035763bmsh11f5f3544eb7004p1fc14fjsn7ae532e3d5c8", # Consider using st.secrets for API keys
	"x-rapidapi-host": "try-on-diffusion.p.rapidapi.com"
}

st.title("Virtual Try-On (RapidAPI)")

# Upload model image (referred to as avatar_image by RapidAPI)
model_image_file = st.file_uploader("Upload Model Image", type=["png", "jpg", "jpeg"], key="model_img_uploader")

# Predefined garment examples (clothing_image for RapidAPI)
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

st.subheader("Choose an outfit:")
if 'selected_garment_info' not in st.session_state:
	st.session_state.selected_garment_info = None # Stores (url, desc, category)

cols_garment = st.columns(len(garment_examples))
for idx, (url, desc, category_val) in enumerate(garment_examples):
	with cols_garment[idx]:
		if st.button(desc, key=f"garment_btn_{idx}"):
			st.session_state.selected_garment_info = (url, desc, category_val)
		try:
			# To avoid re-downloading, consider caching or doing this on selection
			# For simplicity in this example, fetching on each render if not too slow
			img_response = requests.get(url, timeout=5)
			img_response.raise_for_status()
			example_img = Image.open(BytesIO(img_response.content))
			st.image(example_img, caption=desc, use_column_width=True)
		except requests.exceptions.RequestException:
			st.caption(f"Could not load {desc}: Error")
		except IOError:
			st.caption(f"Could not display {desc}")


# Display currently selected predefined garment (optional, for clarity)
if st.session_state.selected_garment_info:
	st.write(f"Selected predefined garment: {st.session_state.selected_garment_info[1]}")

# Upload custom garment image
st.subheader("Or upload your own outfit image:")
custom_garment_file = st.file_uploader("Upload Outfit Image", type=["png", "jpg", "jpeg"], key="custom_garment_uploader")
# The RapidAPI endpoint shown does not use description or category, but we keep UI for parity with app2
# custom_garment_description = st.text_input("Enter Outfit Description (optional)", key="custom_garment_desc") if custom_garment_file else ""
# category_options = ["upper_body", "lower_body", "dresses"] # From app2
# uploaded_garment_category_value = "upper_body" # From app2
# if custom_garment_file:
#     uploaded_garment_category_value = st.selectbox(
#         "Select Garment Category for uploaded image (optional)",
#         category_options,
#         index=0,
#         key="uploaded_category_selector"
#     )

# Button to submit
if st.button("Try On", key="try_on_button"):
	avatar_image_bytes = None
	clothing_image_bytes = None
	avatar_image_name = "avatar.jpg"
	clothing_image_name = "clothing.jpg"

	if model_image_file:
		avatar_image_bytes = model_image_file.getvalue()
		avatar_image_name = model_image_file.name
	else:
		st.error("Please upload a Model Image.")

	if custom_garment_file:
		clothing_image_bytes = custom_garment_file.getvalue()
		clothing_image_name = custom_garment_file.name
		st.session_state.selected_garment_info = None # Clear predefined selection if custom is uploaded
	elif st.session_state.selected_garment_info:
		try:
			garment_url, _, _ = st.session_state.selected_garment_info
			response = requests.get(garment_url)
			response.raise_for_status()
			clothing_image_bytes = response.content
			clothing_image_name = garment_url.split("/")[-1] # Get a name from URL
		except requests.exceptions.RequestException as e:
			st.error(f"Failed to download selected garment: {e}")
			clothing_image_bytes = None # Ensure it's None if download fails
		except Exception as e:
			st.error(f"An error occurred with the selected garment: {e}")
			clothing_image_bytes = None # Ensure it's None if error occurs
	else:
		if model_image_file: # Only show this error if model image is present but garment is not
			st.error("Please choose a predefined outfit or upload your own outfit image.")

	if avatar_image_bytes and clothing_image_bytes:
		with st.spinner("Processing with RapidAPI..."):
			try:
				files_payload = {
					'avatar_image': (avatar_image_name, avatar_image_bytes, model_image_file.type if model_image_file else 'image/jpeg'),
					'clothing_image': (clothing_image_name, clothing_image_bytes, custom_garment_file.type if custom_garment_file else 'image/jpeg')
				}

				api_response = requests.post(RAPIDAPI_URL, files=files_payload, headers=RAPIDAPI_HEADERS)
				api_response.raise_for_status()

				# Display Rate Limit Info
				remaining_requests = api_response.headers.get('x-ratelimit-requests-remaining')
				limit_requests = api_response.headers.get('x-ratelimit-requests-limit')
				
				if remaining_requests and limit_requests:
					st.info(f"API Rate Limit: {remaining_requests} requests remaining out of {limit_requests}.")
				else:
					st.info("Rate limit information not available in response headers.")

				# Assuming the API returns the image directly in the response body
				output_image = Image.open(BytesIO(api_response.content))
				st.image(output_image, caption="Try-On Result from RapidAPI")

			except requests.exceptions.HTTPError as http_err:
				st.error(f"HTTP error occurred: {http_err}")
				st.error(f"Status code: {api_response.status_code}")
				error_content = api_response.text
				try:
					error_json = api_response.json()
					st.json(error_json)
				except ValueError: # If response is not JSON
					st.text_area("API Error Response:", error_content, height=150)
			except requests.exceptions.RequestException as req_err:
				st.error(f"Request error occurred: {req_err}")
			except IOError:
				st.error("Failed to process the image from the API response. The response might not be a valid image.")
				st.text_area("API Response (first 500 chars):", api_response.content[:500], height=150)
			except Exception as e:
				st.error(f"An unexpected error occurred: {str(e)}")
	elif not model_image_file:
		pass # Error already shown
	elif not (custom_garment_file or st.session_state.selected_garment_info):
		pass # Error already shown 
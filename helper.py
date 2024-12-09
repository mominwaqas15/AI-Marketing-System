import os
import qrcode
import base64

OUTPUT_DIR = "Human-Detection-Logs" 

class Helper:
    @staticmethod
    def encode_image(image_path):
        # Check if the file exists
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"The file {image_path} does not exist.")
        
        # Check the file extension
        file_extension = os.path.splitext(image_path)[1].lower()

        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            # If the file is an image
            with open(image_path, "rb") as image_file:
                return [base64.b64encode(image_file.read()).decode('utf-8')]
        else:
            raise ValueError("The provided file is neither an image nor a PDF.")
        
def generate_qr_code(url: str, session_token: str) -> str:
    """
    Generate a QR code for the given URL and save it.
    """
    qr_code_img = qrcode.make(url)
    qr_code_path = f"{OUTPUT_DIR}/qr_{session_token}.png"
    qr_code_img.save(qr_code_path)
    return qr_code_path          
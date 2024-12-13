def generate_qr_code_page(complement: str, qr_code_path: str) -> str:
    """
    Generates the HTML content for the QR Code page.

    :param complement: The complement or message to display.
    :param qr_code_path: Path to the generated QR code image.
    :return: HTML content as a string.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>QR Code for Chat</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                background-color: #f4f4f9;
                color: #333;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }}
            .container {{
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 20px;
                text-align: center;
                width: 90%;
                max-width: 400px;
            }}
            h1 {{
                font-size: 1.5rem;
                color: #007bff;
                margin-bottom: 20px;
            }}
            img {{
                width: 200px;
                height: 200px;
                margin-bottom: 20px;
            }}
            .footer {{
                margin-top: 20px;
                font-size: 0.9rem;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{complement}</h1>
            <p>Scan the QR Code to start chatting on WhatsApp!</p>
            <img src="/static/{qr_code_path}" alt="QR Code">
        </div>
        <div class="footer">
            &copy; 2024 Chat Service. All rights reserved.
        </div>
    </body>
    </html>
    """
    return html_content

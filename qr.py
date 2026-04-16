import qrcode


qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
qr.add_data('https://bbc.com')

data = qr.get_matrix()
print(len(data))
print(data)

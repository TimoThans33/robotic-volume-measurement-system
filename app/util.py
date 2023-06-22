import datetime

""" 
    simple decoder function for SICK default image file name
"""
def sick_img_file_decode(file):
    date = file.split("_")[1:3]
    date = datetime.datetime.strptime("".join(date), "%Y%m%d%H%M%S")
    path = date.strftime('%Y/%m/%d/%H%M%S/')
    return path

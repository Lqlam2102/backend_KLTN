import re
import random

import numpy
from django.utils.text import slugify
from unidecode import unidecode
import string
import unicodedata
from django.contrib.gis.geos import Point, LineString, Polygon, MultiPolygon, GEOSGeometry


def set_name_model(input_string):
    # Loại bỏ dấu tiếng Việt
    no_diacritic_string = remove_diacritic(input_string)

    # Loại bỏ dấu cách, số và ký tự đặc biệt, và viết hoa chữ cái sau mỗi dấu cách hoặc ký tự đặc biệt
    processed_string = remove_special_characters(no_diacritic_string)

    # Thêm 4 chữ ngẫu nhiên vào cuối chuỗi
    final_string = add_random_chars(processed_string)
    return final_string

def remove_diacritic(input_string):
    # Chuẩn hóa chuỗi Unicode để loại bỏ dấu tiếng Việt
    nfkd_form = unicodedata.normalize('NFKD', input_string)
    ascii_string = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
    return ascii_string


def remove_special_characters(input_string):
    # Loại bỏ dấu cách, số và ký tự đặc biệt, và viết hoa chữ cái sau mỗi dấu cách hoặc ký tự đặc biệt
    processed_string = re.sub(r'[^\w\s]', '', input_string)
    processed_string = re.sub(r'\d+', '', processed_string)
    processed_string = re.sub(r'(\s\w)', lambda m: m.group(1).upper(), processed_string)
    processed_string = re.sub(r'\s+', '', processed_string)

    return processed_string


def add_random_chars(input_string):
    # Thêm 4 chữ ngẫu nhiên vào cuối chuỗi
    random_chars = ''.join(random.choices(string.ascii_letters, k=4))
    final_string = input_string + random_chars
    return final_string


def slug_vi(data: str) -> str:
    vietnamese_map = {
        ord(u'o'): 'o', ord(u'ò'): 'o', ord(u'ó'): 'o', ord(u'ỏ'): 'o', ord(u'õ'): 'o', ord(u'ọ'): 'o',
        ord(u'ơ'): 'o', ord(u'ờ'): 'o', ord(u'ớ'): 'o', ord(u'ở'): 'o', ord(u'ỡ'): 'o', ord(u'ợ'): 'o',
        ord(u'ô'): 'o', ord(u'ồ'): 'o', ord(u'ố'): 'o', ord(u'ổ'): 'o', ord(u'ỗ'): 'o', ord(u'ộ'): 'o',

        ord(u'à'): 'a', ord(u'á'): 'a', ord(u'á'): 'a', ord(u'ả'): 'a', ord(u'ã'): 'a', ord(u'ạ'): 'a',
        ord(u'ă'): 'a', ord(u'ắ'): 'a', ord(u'ằ'): 'a', ord(u'ẳ'): 'a', ord(u'ẵ'): 'a', ord(u'ạ'): 'a',
        ord(u'â'): 'a', ord(u'ầ'): 'a', ord(u'ấ'): 'a', ord(u'ậ'): 'a', ord(u'ẫ'): 'a', ord(u'ẩ'): 'a',

        ord(u'đ'): 'd', ord(u'Đ'): 'd',

        ord(u'è'): 'e', ord(u'é'): 'e', ord(u'ẻ'): 'e', ord(u'ẽ'): 'e', ord(u'ẹ'): 'e',
        ord(u'ê'): 'e', ord(u'ề'): 'e', ord(u'ế'): 'e', ord(u'ể'): 'e', ord(u'ễ'): 'e', ord(u'ệ'): 'e',

        ord(u'ì'): 'i', ord(u'í'): 'i', ord(u'ỉ'): 'i', ord(u'ĩ'): 'i', ord(u'ị'): 'i',
        ord(u'ư'): 'u', ord(u'ừ'): 'u', ord(u'ứ'): 'u', ord(u'ử'): 'ữ', ord(u'ữ'): 'u', ord(u'ự'): 'u',
        ord(u'ý'): 'y', ord(u'ỳ'): 'y', ord(u'ỷ'): 'y', ord(u'ỹ'): 'y', ord(u'ỵ'): 'y',

        ord(u'/'): '-'
    }
    slug = slugify(data.translate(vietnamese_map))
    return slug


def no_accent_vietnamese(utf8_str: str) -> str:
    if not utf8_str:
        return ''
    return unidecode(utf8_str)


def import_data_from_geodataframe(gdf, model):
    columns = list(gdf.columns)
    gdf = gdf.replace(numpy.nan, None)

    count_record = 0
    objs = []
    for index, row in gdf.iterrows():
        model_temp = model()
        for column in columns:
            field = no_accent_vietnamese(column).lower()
            data = row[column]
            if field == 'object3d':
                continue
            if column == "geometry":
                field = "geom"
                if data:
                    data = GEOSGeometry(data.wkt)
            setattr(model_temp, field, data)
        objs.append(model_temp)
        count_record += 1
    model.objects.bulk_create(objs)
    return count_record

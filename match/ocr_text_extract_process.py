import os

import cv2
from match.yolov5.detect import detect_qfn, scale_rec
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import fitz

def extract_with_paddle(img_path):
    # Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
    # 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
    ocr = PaddleOCR(use_angle_cls=True,
                    lang="en",
                    det_model_dir="match/ppocr_model/det/en/en_PP-OCRv3_det_infer",
                    rec_model_dir='match/ppocr_model/rec/en/en_PP-OCRv3_rec_infer',
                    cls_model_dir='match/ppocr_model/cls/ch_ppocr_mobile_v2.0_cls_infer'
                    )  # need to run only once to download and load model into memory
    alldata = list()
    boxs = []

    # 读取文件获得boundingbox信息
    with open("tmp_txt/exp/labels/tmp.txt", 'r', encoding='utf-8') as f:
        for ann in f.readlines():
            ann = ann.strip('\n').split(' ')  # 去除文本中的换行符
            ann = [int(x) for x in ann]
            l, t, r, b = scale_rec(ann[1], ann[2], ann[3], ann[4])
            boxs.append((l, t, r, b))
    f.close()

    for num in range(boxs.__len__()):
        croped_img_path = crop_fig_to_paddle_ByYOLO(img_path, num, boxs)
        result = ocr.ocr(croped_img_path, cls=True)
        # for idx in range(len(result)):
        #     res = result[idx]
        #     for line in res:
        #         print(line)

        result = result[0]
        image = Image.open(croped_img_path).convert('RGB')
        boxes = [line[0] for line in result]
        txts = [line[1][0] for line in result]
        scores = [line[1][1] for line in result]
        im_show = draw_ocr(image, boxes, txts, scores)
        im_show = Image.fromarray(im_show)
        im_show.save('tmp_pic/'+'result' + str(num) + '.jpg')

        alldata.append([((x[0][0] + x[1][0]) * 0.5, (x[0][1] + x[2][1]) * 0.5, y) for x, y in zip(boxes, txts) if
                        paddle_filter_noise(y)])
    return alldata


def OCR_method(pdfPath, pageNumber, selectRec, outputPath):
    doc = fitz.open(pdfPath)
    page = doc[pageNumber - 1]
    scale_factor = 4
    pix = page.get_pixmap(matrix=fitz.Matrix(
        scale_factor, scale_factor).prerotate(0))
    img_path = r"./tmp_pic/tmp.png"
    if not os.path.exists("tmp_pic"):  # 判断存放图片的文件夹是否存在
        os.makedirs("tmp_pic")  # 若图片文件夹不存在就创建
    pix.save(img_path)

    # 保存框中的高分tup
    image = cv2.imread(img_path)
    tl = [int(selectRec[0] * scale_factor), int(selectRec[1]*scale_factor)]
    br = [int(selectRec[2] * scale_factor), int(selectRec[3]*scale_factor)]
    cv2.imwrite(img_path,
                image[tl[1]:br[1], tl[0]:br[0]])
    # yolo检测，并将pin的框图片保存以备ocr使用
    detect_qfn()

    print('###################################OCR日志##########################################')
    alldata = extract_with_paddle(img_path)

    def match_text_num(data):
        text_data = []
        num_data = []
        result = []
        for center_x, center_y, text in data:
            if text.isdigit():
                num_data.append((center_x, center_y, text))
            else:
                text_data.append((center_x, center_y, text))
        for center_x, center_y, text in num_data:
            distance_x_list = [(abs(x[1] - center_y),
                                x[2]
                                ) for x in text_data]
            distance_y_list = [(abs(x[0] - center_x),
                                x[2]
                                ) for x in text_data]
            distance_list = distance_x_list + distance_y_list
            matched_text = sorted(distance_list, key=lambda x: x[0])[0][1]
            try:
                result.append((int(text), matched_text))
            except:
                pass

        return result

    result = []
    for data in alldata:
        result = result + sorted(match_text_num(data), key=lambda x: x[0])
    return result


def paddle_filter_noise(txt) -> bool:
    var = not (txt.__eq__('-')
               or txt.__contains__("Fig")
               or txt.__contains__(":")
               or (len(txt) == 1 and not txt.isdigit())
               )
    return var


def crop_fig_to_paddle(img_path, num):
    img = Image.open(img_path)
    save_path = img_path[:-4] + "_" + str(num) + ".jpg"
    boxs = [[0, img.height * 1 / 9, img.width / 3, img.height * 8 / 9],
            [img.width * 1 / 9, img.height * 2 / 3, img.width * 8 / 9, img.height],
            [img.width * 2 / 3, img.height * 1 / 9, img.width, img.height * 8 / 9],
            [img.width * 1 / 9, 0, img.width * 8 / 9, img.height / 3]]
    img = img.crop(boxs[num])
    if num in [0, 2]:
        img.save(save_path)
    else:
        img.rotate(270, expand=1).save(save_path)

    return save_path


def crop_fig_to_paddle_ByYOLO(img_path, num, boxs):
    img = Image.open(img_path)
    save_path = img_path[:-4] + "_" + str(num) + ".jpg"
    img = img.crop(boxs[num])
    l, t, r, b = boxs[num]
    if r-l < b-t:
        img.save(save_path)
    else:
        img.rotate(270, expand=1).save(save_path)
    return save_path

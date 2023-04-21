from paddleocr import PaddleOCR, draw_ocr


import traceback
import fitz


# import tr
import cv2
import time
import os
from PIL import Image, ImageDraw
import numpy as np


from match.pdf_text_extract_process import match_text_num, del_dir, get_original_data_dict
from match.yolov5.detect import detect_qfn, scale_rec


def extractPackage(pdfPath, pageNumber, selectRec, outputPath, tryOCR = False):
    """提取QFN原理图的PinNumber与PinName，并匹配对应后输出到CSV文件：outputPath/pdfName_page_pageNumber.csv

    Args:
        pdfPath (str): pdf的路径
        pageNumber (int): 想要提取的页码
        selectRec (tuple(l,t,r,b)): l,t,r,b分别对应选取区域的左上的x，y与右下的x，y
        outputPath (str):结果输出路径
        tryOCR (bool, optional): 是否强制进行OCR识别 Defaults to False.
    """
    doc = fitz.open(pdfPath)
    page = doc[pageNumber - 1]
    name = pdfPath[pdfPath.rindex('/') + 1:-4]
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

    # 主流程
    result = []
    clip = fitz.Rect(selectRec)  # 想要截取的区域
    try:
        num_data, text_data = get_original_data_dict(
            page, clip)  # x坐标  y坐标  文本
        result = match_text_num(num_data, text_data)
        result = sorted(result, key=lambda x: x[0])
        if result.__len__() == 0 or tryOCR == True:
            1/0
    except Exception as e:
        if e.__class__.__name__.__eq__("ZeroDivisionError"):
            print("最终结果是空或自主OCR")
        else:
            print("PyMuPDF方法报错,实行OCR识别,报错信息如下：")
            print("大概率是加密PDF或者不规则或是图片")
            traceback.print_exc()
        try:
            result = plan_B(img_path)
        except:
            print("OCR方法报错,文件{}没有结果,报错信息如下：".format(name))
            traceback.print_exc()
    # print(result)
    # print("1.所复制内容为：" + str(a_text))
    # pyperclip.copy(a_text)
    print("完成复制")
    data = {"Number": [x[0] for x in result], "Name": [x[1] for x in result]}
    # data['Electrical Type'] = []
    # data['Graphic Style'] = []
    import pandas as pd
    df = pd.DataFrame(data)
    if not os.path.exists(outputPath):
        os.mkdir(outputPath)
    
    if 1 == 0:#方便测试
        save_path = outputPath + '/' + name + \
            '_page_' + str(pageNumber - 1 + 1) + "_0.csv"
        while os.path.exists(save_path):
            save_path = save_path[:-5] + str(int(save_path[-5]) + 1) + '.csv'
    else:
        save_path = outputPath + '/' + name + \
            '_page_' + str(pageNumber - 1 + 1) + ".csv"
    df.to_csv(path_or_buf=save_path,sep=',',header=True,index=False)

    # 这里是删除tmp
    del_dir('tmp_pic')
    del_dir('tmp_txt')


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


def tr_filter_noise(rec) -> bool:
    var = rec[2] > 0.7 and (
        not (rec[1].__contains__("-") or rec[1].__contains__("Fig") or rec[1].__contains__(":") or rec[
            1].isdigit() or rec[1].__contains__("(") or rec[1].__contains__(")") or rec[1].__len__() < 2
        ))
    return var


def process_img_to_tr(img_path):
    mat_img = cv2.imread(img_path)
    mat_img2 = cv2.cvtColor(mat_img, cv2.COLOR_BGR2GRAY)
    dst1 = \
        cv2.adaptiveThreshold(
            mat_img2, 255, cv2.BORDER_REPLICATE, cv2.THRESH_BINARY_INV, 19, 6)
    k1 = np.ones((1, 1), dtype=np.uint8)
    dst1 = cv2.morphologyEx(dst1, cv2.MORPH_DILATE, k1)
    contours1, heridency1 = \
        cv2.findContours(dst1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour1 = sorted(contours1, key=cv2.contourArea, reverse=True)[0]
    cv2.drawContours(mat_img, contour1, -1, (255, 0, 255), 1)
    rest1 = cv2.boundingRect(contour1)

    mat_img[rest1[1]:rest1[1] + rest1[3], rest1[0]:rest1[0] + rest1[2]] = 255
    cv2.imwrite(img_path[:-4] + '_white.jpg', mat_img)
    mat_img2 = cv2.cvtColor(mat_img, cv2.COLOR_BGR2GRAY)
    dst2 = \
        cv2.adaptiveThreshold(
            mat_img2, 255, cv2.BORDER_REPLICATE, cv2.THRESH_BINARY_INV, 19, 6)
    k2 = np.ones(
        (mat_img.shape[0] // 30, mat_img.shape[0] // 30), dtype=np.uint8)
    dst2 = cv2.morphologyEx(dst2, cv2.MORPH_DILATE, k2)
    contours2, heridency2 = \
        cv2.findContours(dst2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour2 = sorted(contours2, key=cv2.contourArea, reverse=True)[0:4]
    rest2 = [cv2.boundingRect(i) for i in contour2]  # 得到这条轮廓的外接矩阵
    # print(rest2)
    rest2 = sorted(rest2, key=lambda x: x[0])
    # print(img_path[:-4] + '_{}.jpg'.format(i))
    # print(rest2[i])

    ans = rest2[0]
    del rest2[0]
    i = 0
    cv2.imwrite(img_path[:-4] + '_{}.jpg'.format(i),
                mat_img[ans[1]:ans[1] + ans[3], ans[0]:ans[0] + ans[2]])
    ans = rest2[-1]
    del rest2[-1]
    i = 2
    cv2.imwrite(img_path[:-4] + '_{}.jpg'.format(i),
                mat_img[ans[1]:ans[1] + ans[3], ans[0]:ans[0] + ans[2]])

    rest2 = sorted(rest2, key=lambda x: x[1])

    ans = rest2[0]
    del rest2[0]
    i = 3
    cv2.imwrite(img_path[:-4] + '_{}.jpg'.format(i),
                mat_img[ans[1]:ans[1] + ans[3], ans[0]:ans[0] + ans[2]])
    ans = rest2[-1]
    del rest2[-1]
    i = 1
    cv2.imwrite(img_path[:-4] + '_{}.jpg'.format(i),
                mat_img[ans[1]:ans[1] + ans[3], ans[0]:ans[0] + ans[2]])


def extract_with_tr(img_path, num) -> list[str]:
    # print("recognize", tr.recognize("imgs/line.png"))

    # img_path = "qfn_3.jpg"
    # img_path = "imgs/name_card.jpg"

    img_pil = Image.open(img_path)
    if num in [1, 3]:
        img_pil = img_pil.rotate(270, expand=True)
    try:
        if hasattr(img_pil, '_getexif'):
            # from PIL import ExifTags
            # for orientation in ExifTags.TAGS.keys():
            #     if ExifTags.TAGS[orientation] == 'Orientation':
            #         break
            orientation = 274
            exif = dict(img_pil._getexif().items())
            if exif[orientation] == 3:
                img_pil = img_pil.rotate(180, expand=True)
            elif exif[orientation] == 6:
                img_pil = img_pil.rotate(270, expand=True)
            elif exif[orientation] == 8:
                img_pil = img_pil.rotate(90, expand=True)
    except:
        pass

    MAX_SIZE = 1600
    if img_pil.height > MAX_SIZE or img_pil.width > MAX_SIZE:
        scale = max(img_pil.height / MAX_SIZE, img_pil.width / MAX_SIZE)

        new_width = int(img_pil.width / scale + 0.5)
        new_height = int(img_pil.height / scale + 0.5)
        img_pil = img_pil.resize((new_width, new_height), Image.ANTIALIAS)

    color_pil = img_pil.convert("RGB")
    gray_pil = img_pil.convert("L")

    img_draw = ImageDraw.Draw(color_pil)
    colors = ['red', 'green', 'blue', "purple"]

    t = time.time()
    n = 1
    for _ in range(n):
        tr.detect(gray_pil, flag=tr.FLAG_RECT)
    print("time", (time.time() - t) / n)

    results = tr.run(gray_pil, flag=tr.FLAG_ROTATED_RECT)

    results = [rec for rec in results if tr_filter_noise(rec)]
    for i, rect in enumerate(results):
        cx, cy, w, h, a = tuple(rect[0])
        # print(i, "\t", rect[1], rect[2])
        box = cv2.boxPoints(((cx, cy), (w, h), a))
        box = np.int0(np.round(box))

        for p1, p2 in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            img_draw.line(xy=(box[p1][0], box[p1][1], box[p2][0],
                          box[p2][1]), fill=colors[i % len(colors)], width=2)

    color_pil.save(img_path)

    return [text for (_, text, _) in results]


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


def plan_B(img_path):

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


if __name__ == '__main__':
    # from figure_extract import *
    # # import untils
    #
    # filt = pdftool()  # 通过扫描法获取图片并存于Figs
    # pdf_path = f"Symbol/00002304A_p6.pdf"
    # pathlist: list[str] = list
    # filt.set_pdf_path(pdf_path)
    # tittle_list = filt.extract_tittle_list(5)
    # for tittle in tittle_list:
    #     if tittle.__contains__("QFN"):
    #         print(tittle_list)
    #         list = filt.extract_tittle_coordinates_up_bottom(5)  # 提取标题坐标
    #         filt.extract_figure_by_tittle_coordinates(5, list)

    result = []
    img_path = 'TestFigs/images+27.jpg'
    process_img_to_tr(img_path)
    for num in range(4):
        # croped_img_path = crop_fig(img_path, num)

        # ans = extract_with_tr(croped_img_path[:-4]+'.jpg',num)#恩分
        ans = extract_with_tr(
            img_path[:-4] + '_' + str(num) + '.jpg', num)  # 边缘检测分割自动分四块
        if num in [2, 3]:
            result = result + list(reversed(ans))
        else:
            result = result + ans
    # print(result)
    # print(result.__len__())
    data = {}
    data["Number"] = [_ for _ in range(1, result.__len__() + 1)]
    data["Name"] = result
    # data['Electrical Type'] = []
    # data['Graphic Style'] = []
    import pandas as pd

    df = pd.DataFrame(data)
    df.to_excel("out_" + img_path[9:-4] + ".xlsx",
                sheet_name="sheet1", startcol=0, index=False)

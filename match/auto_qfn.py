import shutil
import traceback
import fitz


# import tr
import cv2
import time
import os
from PIL import Image, ImageDraw
import numpy as np
from match.ocr_text_extract_process import OCR_method
from match.pdf_text_extract_process import fitz_method


def extractPackage(pdfPath, pageNumber, selectRec, outputPath, tryOCR=False):
    """提取QFN原理图的PinNumber与PinName，并匹配对应后输出到CSV文件：outputPath/pdfName_page_pageNumber.csv

    Args:
        pdfPath (str): pdf的路径
        pageNumber (int): 想要提取的页码
        selectRec (tuple(l,t,r,b)): l,t,r,b分别对应选取区域的左上的x，y与右下的x，y
        outputPath (str):结果输出路径
        tryOCR (bool, optional): 是否强制进行OCR识别 Defaults to False.
    """

    name = pdfPath[pdfPath.rindex('/') + 1:-4]
    result = []
    # 主流程
    try:
        result = fitz_method(pdfPath, pageNumber, selectRec, outputPath)
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
            result = OCR_method(pdfPath, pageNumber, selectRec, outputPath)
        except:
            print("OCR方法报错,文件{}没有结果,报错信息如下：".format(name))
            traceback.print_exc()
        finally:
            # 这里是删除tmp
            del_dir('tmp_pic')
            del_dir('tmp_txt')
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

    if 1 == 0:  # 方便测试
        save_path = outputPath + '/' + name + \
            '_page_' + str(pageNumber - 1 + 1) + "_0.csv"
        while os.path.exists(save_path):
            save_path = save_path[:-5] + str(int(save_path[-5]) + 1) + '.csv'
    else:
        save_path = outputPath + '/' + name + \
            '_page_' + str(pageNumber - 1 + 1) + ".csv"
    df.to_csv(path_or_buf=save_path, sep=',', header=True, index=False)

 

def del_dir(path):
    filelist = []
    rootdir = path  # 选取删除文件夹的路径,最终结果删除img文件夹
    filelist = os.listdir(rootdir)  # 列出该目录下的所有文件名
    for f in filelist:
        filepath = os.path.join(rootdir, f)  # 将文件名映射成绝对路劲
        if os.path.isfile(filepath):  # 判断该文件是否为文件或者文件夹
            os.remove(filepath)  # 若为文件，则直接删除
            # print(str(filepath)+" removed!")
        elif os.path.isdir(filepath):
            shutil.rmtree(filepath, True)  # 若为文件夹，则删除该文件夹及文件夹内所有文件
            # print("dir "+str(filepath)+" removed!")
    shutil.rmtree(rootdir, True)  # 最后删除img总文件夹
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

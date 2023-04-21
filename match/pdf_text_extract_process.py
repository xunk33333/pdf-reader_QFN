from decimal import Decimal
import os
import pickle
import re
import shutil
import matplotlib.path as mplPath
import numpy as np


def match_text_num(num_data, text_data, threshold=7):
    result = []

    for center_x, center_y, text in num_data:
        distance_x_list = [(abs(x[1] - center_y),
                            x[2]
                            ) for x in text_data if abs(x[0] - center_x) < threshold]
        distance_y_list = [(abs(x[0] - center_x),
                            x[2]
                            ) for x in text_data if abs(x[1] - center_y) < threshold]
        distance_list = distance_x_list + distance_y_list
        matched_text = sorted(distance_list, key=lambda x: x[0])[0][1]
        result.append((int(text), matched_text))
    return result


def text_filter(txt):

    var = not (re.search("QFN", txt, re.IGNORECASE)
               or re.search("view", txt, re.IGNORECASE)
               or re.search("top", txt, re.IGNORECASE)
               or re.search("Thermal", txt, re.IGNORECASE)
               or re.search("pad", txt, re.IGNORECASE)
               or re.search(",", txt, re.IGNORECASE)
               )

    return var


def successive_digit(txt):
    words = [x for x in txt.split(' ') if not x == '']
    for word in words:
        if not word.isdigit():
            return False
    return True


def concat_span_text(line_spans):
    if line_spans.__len__() == 1:
        return line_spans[0]['text']
    else:
        text = ''
        for span in line_spans:
            text = text + span['text']
        return text


def split_span_text(lines):
    lines_copy = lines.copy()
    for line in lines_copy:
        spans = line['spans']
        if spans.__len__() == 1 and spans[0]['text'].__contains__(' '):
            lines.remove(line)
            span = spans[0]
            words = span['text'].split(' ')
            l, t, r, b = span['bbox']
            w = r - l
            h = b - t
            sum_len = len(span['text'])

            s_w = w/sum_len
            y_center = t + h/2
            dis_num = 0
            for i, word in enumerate(words):
                left = l + s_w*(dis_num+i)
                dis_num += len(word)
                right = left + s_w*len(word)
                x_center = left/2 + right/2
                lines.append({'text': word,
                              'origin': (x_center, y_center),
                              'spans': [
                                  {
                                      "size": span['size'],
                                      'origin':(x_center, y_center)
                                  }
                              ],
                              'dir': line['dir']
                              })


def concat_line_text(lines):
    # 拼接下标
    standard_font_size = lines[0]['spans'][0]['size']
    concated_lines = []
    # 1 比较字体大小，找到下标字体.
    for line in lines.copy():
        try:
            # 2 根据角度dir，区分拼接顺序与筛选条件：5与50
            if standard_font_size - line['spans'][0]['size'] > 1:
                # if True:
                concated_line = concat_subscript_text(lines, line)
                if concated_line is not None:
                    concated_lines.append(concated_line)
        except:
            continue  # 由于split span后新加入的line不规范，没有，key：spans所以跳过
    lines += concated_lines


def concat_subscript_text(lines, subline, threshold1=5, threshold2=50):
    """拼接line，目前只有横向的左到右的拼接
    注：拼接后会把所有涉及到的line从lines中移除
    Args:
        lines (_type_): 当前的所有line
        subline (_type_): 根据字体大小，找到的下标字体对应的line
        threshold1 (int, optional): 小阈值. 以左到右为例，为了筛除上下相邻的 Defaults to 5.
        threshold2 (int, optional): 大阈值. 以左到右为例，确定左右范围，防止把对面的也拼进来 Defaults to 50.

    Returns:
        _type_: 拼接好的line，如果没拼接则会返回None
    """
    lines_copy = lines.copy()
    potential_match = []

    if subline['dir'][0] == 1:  # 左到右拼接
        for line in lines_copy:
            if line['text'].isdigit():
                continue
            elif abs(line['spans'][0]['origin'][1] - subline['spans'][0]['origin'][1]) < threshold1 and abs(
                    line['spans'][0]['origin'][0] - subline['spans'][0]['origin'][0]) < threshold2:
                potential_match.append(
                    (line['spans'][0]['origin'], line['text']))
                lines.remove(line)

        text = ''
        origin_x = 0
        origin_y = 0
        for origin, txt in sorted(potential_match, key=lambda x: x[0][0]):
            if not txt.isdigit():
                text += txt
                origin_x += origin[0]
                origin_y += origin[1]
        if potential_match.__len__() == 0:
            return None

        concated_line = {'text': text,
                         'origin': (origin_x / potential_match.__len__(), origin_y / potential_match.__len__())}
        return concated_line

    elif abs(subline['dir'][0]) < 0.1 and subline['dir'][0] > 0:  # 下到上拼接
        pass
    else:  # 上到下拼接
        pass


def get_original_data_dict(page, clip):
    """获取已经处理好的numdata与textdata

    处理流程：
            1）获取所有line放入列表lines
            2）把一个line中存在多个span的，给拼接起来结果放在line['text']，然后顺便进行一次多余数据的筛除
            3）筛选出所有的num，存入num_data，并把对应的line在lines中去除
            4）根据num_data围成多边形，按比例缩小多边形，去除多边形内部数据
            5）连接line与line
            6）一些特殊情况的处理

    Args:
        page (fitz.Page): 对应页面
        clip (fitz.Rect): 矩形区域

    Returns:
        num_data, text_data: 存储数据的列表
        单个数据格式（center_x, center_y, text）
    """
    blocks = page.get_text("dict", clip=clip)['blocks']
    lines = []
    data = []
    text_data = []
    num_data = []
    for block in blocks:
        # if block['lines'].__len__() != 1:
        #     concat_line_flag = False
        lines = lines + block['lines']

    # 处理span拆成多个line，主要针对数字
    # split_span_text(lines) #拆开后会导致line信息丢失，暂时关闭

    # 拼接同一个line不同span中的字符
    for line in lines.copy():
        try:
            line['text'] = concat_span_text(line['spans'])
            if line['spans'].__len__() == 0 or not text_filter(line['text']):
                lines.remove(line)
        except:
            continue  # 由于split span后新加入的line不规范，没有，key：spans所以跳过

    

    #获得num_data
    for line in lines.copy():
        if line['text'].isdigit():
            num_data.append((line['bbox'][0] / 2 + line['bbox'][2] / 2,
                         line['bbox'][1] / 2 + line['bbox'][3] / 2,
                         line['text'])
                        )
            lines.remove(line)
            
    # 上面获取num——data有问题，所以用下面方法补充
    words = page.get_text("words", clip=clip)
    for _, _, right, bottom, txt, block_no, line_no, word_no in words:
        if txt.isdigit() and txt not in [x[2] for x in num_data]:
            num_data.append((right-2, bottom-2, txt))
    
    #########################此时的lines里只剩下text_data#########################

    # 给数字排个序
    num_data = [(x, y, int(txt)) for x, y, txt in num_data]
    num_data = sorted(num_data, key=lambda x: int(x[2]))
    if num_data[-1][2] % 2 == 1:  # 删除奇数
        num_data.pop(-1)
    
    # 去除框内的多余的text
    def get_gravity_point(points):
        """
        @brief      获取多边形的重心点
        @param      points  The points
        @return     The center of gravity point.
        """
        if len(points) <= 2:
            return list()

        area = Decimal(0.0)
        x, y = Decimal(0.0), Decimal(0.0)
        for i in range(len(points)):
            lng = Decimal(points[i][0])
            lat = Decimal(points[i][1])
            nextlng = Decimal(points[i-1][0])
            nextlat = Decimal(points[i-1][1])

            tmp_area = (nextlng*lat - nextlat*lng)/Decimal(2.0)
            area += tmp_area
            x += tmp_area*(lng+nextlng)/Decimal(3.0)
            y += tmp_area*(lat+nextlat)/Decimal(3.0)
        x = x/area
        y = y/area
        return [float(x), float(y)]

    def create_equal_ratio_points(points, ratio, gravity_point):
        """
        @brief      创建等比例的点
        @param      points         The points
        @param      ratio          The ratio
        @param      gravity_point  The gravity point
        @return     { description_of_the_return_value }
        """
        # 判断输入条件
        if len(points) <= 2 or not gravity_point:
            return list()

        new_points = list()
        length = len(points)

        for i in range(length):
            vector_x = points[i][0] - gravity_point[0]
            vector_y = points[i][1] - gravity_point[1]
            new_point_x = ratio * vector_x + gravity_point[0]
            new_point_y = ratio * vector_y + gravity_point[1]
            new_point = [new_point_x, new_point_y]
            new_points.append(new_point)
        return new_points

    num_points = [[x, y] for x, y, _ in num_data]
    num_points = create_equal_ratio_points(
        num_points, 0.8, get_gravity_point(num_points))
    poly_path = mplPath.Path(np.array(num_points))
    for line in lines.copy():
        center_x, center_y, text = (line['bbox'][0] / 2 + line['bbox'][2] / 2,
                         line['bbox'][1] / 2 + line['bbox'][3] / 2,
                         line['text'])
        if poly_path.contains_point((center_x, center_y)):
            lines.remove(line)
    

    # 连接line line的text
    concat_line_text(lines)        

    for line in lines:
        if successive_digit(line['text']):#去除“16  15 14  13”类
            continue
        elif line.get('bbox') is not None:
            text_data.append((line['bbox'][0] / 2 + line['bbox'][2] / 2,
                         line['bbox'][1] / 2 + line['bbox'][3] / 2,
                         line['text'])
                        )
        else:
            text_data.append((line['origin'][0],
                        line['origin'][1],
                        line['text'])
                        )


    # 数字 字符在一个span中的特殊情况处理
    def synthetic_num_txt(text):
        words = [x for x in text.split(' ') if not x == '']
        if words.__len__() == 2:
            if words[0].isdigit() and not words[1].isdigit():
                return words[1]
            elif words[1].isdigit() and not words[0].isdigit():
                return words[0]
            else:
                return text
        else:
            return text
    text_data = [(center_x, center_y, synthetic_num_txt(text))
                 for center_x, center_y, text in text_data]
    
    #多余空格的特殊情况处理
    text_data = [(center_x, center_y, text[1:]) 
                 if text[0].__eq__(' ')
                 else (center_x, center_y, text)
                 for center_x, center_y, text in text_data]

    return num_data, text_data

def get_original_data_words(page, clip):
    num_data = []
    text_data = []
    data = [(x[2], x[3], x[4]) for x in page.get_text("words", clip=clip)]  # x坐标  y坐标  文本
    for center_x, center_y, text in data:
        if text.isdigit():
            num_data.append((center_x, center_y, int(text)))
        else:
            text_data.append((center_x, center_y, text))

    num_data = sorted(num_data, key=lambda x: int(x[2]))#排序
    if num_data[-1][2] % 2 == 1:  # 删除奇数
        num_data.pop(-1)
        
    return num_data, text_data

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

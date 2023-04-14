import os
import pickle
import re
import shutil


def match_text_num(num_data,text_data, threshold=7):
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
               )
    

    return var
def successive_digit(txt):
    words = [x for x in txt.split(' ') if not x=='']
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
            l,t,r,b = span['bbox']
            w = r - l
            h = b - t
            sum_len = len(span['text'])

            s_w = w/sum_len
            y_center = t + h/2
            dis_num = 0
            for i,word in enumerate(words):
                left = l + s_w*(dis_num+i)
                dis_num += len(word) 
                right = left + s_w*len(word)
                x_center = left/2 + right/2
                lines.append({'text': word,
                         'origin': (x_center,y_center),
                         'spans':[
                                {
                                    "size":span['size'],
                                    'origin':(x_center,y_center)
                                }
                         ],
                         'dir':line['dir']
                         })
            

            

def concat_line_text(lines):
    

    #拼接同一个line不同span中的字符
    lines_copy = lines.copy()
    for line in lines_copy:
        try:
            line['text'] = concat_span_text(line['spans'])
            if line['spans'].__len__() == 0 or not text_filter(line['text']):
                lines.remove(line)
        except:
            continue#由于split span后新加入的line不规范，没有，key：spans所以跳过
    
    #拼接下标
    concated_lines = []
    # 1 比较字体大小，找到下标字体.
    standard_font_size = lines[0]['spans'][0]['size']
    lines_copy = lines.copy()
    for line in lines_copy:
        try:
            if standard_font_size - line['spans'][0]['size'] > 1:  # 2 根据角度dir，区分拼接顺序与筛选条件：5与50
            #if True:
                concated_line = concat_subscript_text(lines, line)
                if concated_line is not None:
                    concated_lines.append(concated_line)
        except:
            continue#由于split span后新加入的line不规范，没有，key：spans所以跳过
    lines += concated_lines


def concat_subscript_text(lines, subline, threshold1=5, threshold2=50):
    lines_copy = lines.copy()
    potential_match = []

    if subline['dir'][0] == 1:  # 左到右拼接
        for line in lines_copy:
            if line['text'].isdigit():
                continue
            elif abs(line['spans'][0]['origin'][1] - subline['spans'][0]['origin'][1]) < threshold1 and abs(
                    line['spans'][0]['origin'][0] - subline['spans'][0]['origin'][0]) < threshold2:
                potential_match.append((line['spans'][0]['origin'], line['text']))
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


def get_original_data(page, clip):
    blocks = page.get_text("dict", clip=clip)['blocks']
    lines = []
    data = []
    text_data = []
    num_data = []
    for block in blocks:
        # if block['lines'].__len__() != 1:
        #     concat_line_flag = False
        lines = lines + block['lines']

    #处理span拆成多个line，主要针对数字
    # split_span_text(lines) #拆开后会导致line信息丢失，暂时关闭

    #连接line line的text
    concat_line_text(lines)

    for line in lines:
        if line.get('bbox') is not None:
            data.append((line['bbox'][0] / 2 + line['bbox'][2] / 2,
                         line['bbox'][1] / 2 + line['bbox'][3] / 2,
                         line['text'])
                        )
        else:
            data.append((line['origin'][0],
                        line['origin'][1],
                        line['text'])
                        )
    
    for center_x, center_y, text in data:
        if text.isdigit():
            num_data.append((center_x, center_y, text))
        elif successive_digit(text):
            continue
        else:
            text_data.append((center_x, center_y, text))

    #上面获取num——data有问题，所以用下面方法补充
    words = page.get_text("words", clip=clip)
    for _,_,right,bottom,txt,block_no,line_no,word_no in words:
        if txt.isdigit() and txt not in [x[2] for x in num_data]:
            num_data.append((right-2, bottom-2, txt))

    #数字 字符在一个span中的特殊情况处理
    def synthetic_num_txt(text):
        words = [x for x in text.split(' ') if not x=='']
        if words.__len__()==2:
            if words[0].isdigit() and not words[1].isdigit():
                return words[1]
            elif words[1].isdigit() and not words[0].isdigit():
                return words[0]
        else:
            return text
    text_data = [(center_x, center_y,synthetic_num_txt(text))
                  for center_x, center_y, text in text_data ]
    
    return num_data,text_data


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


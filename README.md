# 2023年5月10日
### 改动
1. 去除YOLO与PaddleOCR模块，代码目前只针对可编辑PDF
2. 修复部分匹配bug
### 问题解决情况
- LT3756-3756-1-3756-2
  - page_2_0    ✅
- 2282fb
  - page_2_0    ✅
- msp430g2412
  - page_3_0    ❌   PinName字符过长
  - page_3_1    ❌   PinName字符过长
  - page_3_2    ❌   PinName字符过长
- slrs023e
  - page_3_0    ❌   不可编辑
- drv8801 (*)
  - page_3_1    ❌   解决问题（pin number融合到name中），而造成的影响。例如：MODE 2（正确）与 5 SPILIT（错误）处理后变成 MODE（错误）与 SPILIT（正确）
  - page_3_3    ❌   同上
- dac5578
  - page_5_1    ✅   
- CY8CMBR3002_P9
  - page_13_0   ✅
  - page_15_0   ❌   存在隐藏字符（即表面看不见，但选中粘贴会看到结果）
  - page_15_1   ❌   存在隐藏字符（即表面看不见，但选中粘贴会看到结果）
# 2023年5月5日
## （0504）版本代码的結果反饋
### 问题总结：
- LT3756-3756-1-3756-2
  - page_2_0
- 2282fb
  - page_2_0
- msp430g2412
  - page_3_0
  - page_3_1
  - page_3_2
- slrs023e
  - page_3_0
- drv8801 (*)
  - page_3_1
  - page_3_3
- dac5578
  - page_5_1
- CY8CMBR3002_P9
  - page_13_0
  - page_15_0
  - page_15_1
![0504feedback](../pdf-reader_QFN/feedback/0504feedback.png "0504feedback")
# 2023年5月4日
### 改动
1. extractPackage接口新增参数tryOCR
2. 加入了YOLOv5进行Pin脚检测来辅助OCR流程
3. 对代码添加了一些注释
4. 输出改成csv文件格式
5. 优化了输出日志与异常退出
6. 直接处理结果来解决（0411）的问题2，4
7. 利用pin number围成多边形筛除中间字符干扰
# 2023年4月19日
## （0411）版本代码的結果反饋
### 问题总结：
1. 建议后面提供迭代版本也都改成csv文件格式
2. pin number融合到name中
3. 中间字符干扰
4. 有多余空格
5. 器件中心没有名字的pin编号识别（可归为问题3）
6. 存在隐藏字符（即表面看不见，但选中粘贴会看到结果）
7. 异常退出
![0411feedback](../pdf-reader_QFN/feedback/0411feedback.png "0411feedback")

## （0303）版本代码主要问题
1. 中间字符干扰
2. 字符缺失

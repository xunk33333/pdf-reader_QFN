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

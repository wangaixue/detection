# -*- coding: utf-8 -*-
# crop affine channel_shuffle blur salt_and_pepper

import numpy as np
from PIL import Image
import cv2
import os

import imgaug as ia
from imgaug import augmenters as iaa

ia.seed(1)


def readlist(file):
    dict = {}
    count0 = 0
    count = 0
    with open(file, 'r') as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            if '/' in lines[i]:
                img_id  = lines[i].rstrip().split(' ')[0].split('/')[-1]
                # print('img_id=',img_id)
                # int()只能转化由纯数字组成的字符串，非纯数字会报如下错
                # ValueError: invalid literal for int() with base 10
                # 这里取得是雨伞的数量
                num = int(lines[i].rstrip().split(' ')[1])
                # print('num = ',num)

                if num == 0:
                    count0 = count0 + 1
                    continue

                # if dict.has_key(img_id):
                if img_id in dict:
                    count = count + 1
                dict[img_id] = np.zeros((num, 4))

                coordinations = []
                j = 0 # 控制每一行中坐标的读取

                for box_idx in range(num):
                    # 取每一行中标记的坐标(x,y,w,h)
                    coordinations = lines[i].rstrip().split(' ')[2:]
                    x, y, w, h = map(int,coordinations[j:j+4])
                    dict[img_id][box_idx, 0:4] = [x, y, w, h]
                    j = j + 4

                i = i + 1 # 按行读取文件中的所有行
            else:
                continue
    return dict


def writelist(fp, img_id, bboxes):
    fp.write('OID/train/Umbrella/'+img_id + ' ')
    box_num = len(bboxes)
    fp.write(str(box_num)+' ')
    for bbox in bboxes:
        x = int(round(bbox.x1))
        y = int(round(bbox.y1))
        w = int(round(bbox.x2 - bbox.x1))
        h = int(round(bbox.y2 - bbox.y1))
        fp.write('{} {} {} {} '.format(x, y, w, h))
    fp.write('\n')
    return fp


def main():
    # datapath为存放训练图片的地方
    datapath = '/home/zhex/data/OID_origin/train/Umbrella/'
    # original_file为需要被增强的
    original_file = '/home/zhex/data/OID_origin/tools/new_txt/Umbrella.txt'  # 需要被增强的训练真值txt
    # aug_file只记录了新增的增强后图片的box，要得到原始+增强的所有label：cat original_file augfile>finalfile(txt拼接)
    # aug_file输出是pdpd需要的格式，pytorch需要另行转换(可以拼接得到finalfile后直接将finalfile转换)
    aug_file = 'augfile_Umbrella.txt'
    dict_before = readlist(original_file)
    new_fp = open(aug_file, 'w')
    # augscene = {'Umbrellad':10,'hat':2}  # 需要哪些场景，新增几倍数量的新数据
    augscene = {'Umbrella': 5}
    for scene in augscene:# scene = Umbrella img_id = scene
        for i in range(augscene[scene]):
            for img_id in dict_before.keys():
                img = Image.open(datapath + img_id)
                img = np.array(img)
                bbs = ia.BoundingBoxesOnImage(
                    [ia.BoundingBox(x1=x, y1=y, x2=x+w, y2=y+h) for [x, y, w, h] in dict_before[img_id]],
                    shape=img.shape)

                # 设置数据增强方式
                seq = iaa.SomeOf((1, 3), [
                    iaa.Crop(px=(0, 16)),     #裁剪
                    iaa.Multiply((0.7, 1.3)), #改变色调
                    iaa.Affine(
                        scale=(0.5, 0.7)),     #放射变换
                    iaa.GaussianBlur(sigma=(0, 1.5)),  #高斯模糊
                    # iaa.AddToHueAndSaturation(value=(25,-25)),
                    iaa.ChannelShuffle(1),  # RGB三通道随机交换
                    iaa.ElasticTransformation(alpha=0.1),
                    # iaa.Grayscale(alpha=(0.2, 0.5)),
                    iaa.Pepper(p=0.03),
                    iaa.AdditiveGaussianNoise(scale=(0.03 * 255, 0.05 * 255)),
                    iaa.Dropout(p=(0.03, 0.05)),
                    iaa.Salt(p=(0.03, 0.05)),
                    iaa.AverageBlur(k=(1, 3)),
                    iaa.Add((-10, 10)),
                    iaa.CoarseSalt(size_percent=0.01)
                ])
                seq_det = seq.to_deterministic()  # 保持坐标和图像同步改变，每个batch都要调用一次，不然每次的增强都是一样的
                image_aug = seq_det.augment_images([img])[0]
                bbs_aug = seq_det.augment_bounding_boxes([bbs])[0]

                pic_name = img_id.split('.')[0]

                # datapath = '/home/zhex/OID/train/Umbrella'
                if not os.path.exists(datapath + 'myaug/'):
                    os.makedirs(datapath + 'myaug/')
                new_img_id = 'myaug/' + pic_name + '_{}'.format(i) + '.jpg'
                print('new_img_id = ',new_img_id)
                Image.fromarray(image_aug).save(datapath + new_img_id)
                new_fp = writelist(new_fp, new_img_id, bbs_aug.bounding_boxes)


if __name__ == '__main__':
    main()


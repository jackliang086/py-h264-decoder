import PIL
import  numpy as np
from PIL import Image
import os
import shutil

def make_output_folder():
    if os.path.exists('output/'):
        shutil.rmtree('output')
    os.mkdir('output')

def output_slice_2_png(slice):
    width = slice.PicWidthInSamples_L
    height = slice.PicHeightInSamples_L

    uv_width = width // 2
    uv_height = height // 2

    Y = np.zeros((height, width), np.uint8, 'C')
    U = np.zeros((uv_height, uv_width), np.uint8, 'C')
    V = np.zeros((uv_height, uv_width), np.uint8, 'C')

    for m in range(height):
        for n in range(width):
            Y[m,n] = slice.S_prime_L[n][m]
    for m in range(uv_height):
        for n in range(uv_width):
            V[m,n] = slice.S_prime_Cr[n][m]
            U[m,n] = slice.S_prime_Cb[n][m]

    rgb = yuv2rgb(Y, U, V, width, height)
    im_r = Image.fromarray(rgb[0], 'L')
    im_g = Image.fromarray(rgb[1], 'L')
    im_b = Image.fromarray(rgb[2], 'L')
    im_merge = Image.merge('RGB', (im_r, im_g, im_b))

    img_name = 'output/' + str(slice.ThisPoc) + '_' + slice.slice_type + '.png'
    im_merge.save(img_name, 'png')


def readYuvFile(width, height):
    yf = open('./Luma','r')
    uf = open('./Cb', 'r')
    vf = open('./Cr', 'r')

    uv_width=width//2
    uv_height=height//2

    Y=np.zeros((height,width),np.uint8,'C')
    U=np.zeros((uv_height,uv_width),np.uint8,'C')
    V=np.zeros((uv_height,uv_width),np.uint8,'C')

    for m in range(height):
        for n in range(width):
            Y[m,n] = int(yf.readline().strip('\n'))
    for m in range(uv_height):
        for n in range(uv_width):
            V[m,n] = int(vf.readline().strip('\n'))
            U[m,n] = int(uf.readline().strip('\n'))

    yf.close()
    uf.close()
    vf.close()
    return (Y,U,V)

def yuv2rgb(Y, U, V, width, height):
    U=np.repeat(U,2,0)
    U=np.repeat(U,2,1)
    V=np.repeat(V,2,0)
    V=np.repeat(V,2,1)
    rf=np.zeros((height,width),float,'C')
    gf=np.zeros((height,width),float,'C')
    bf=np.zeros((height,width),float,'C')

    rf=Y+1.14*(V-128.0)
    gf=Y-0.395*(U-128.0)-0.581*(V-128.0)
    bf=Y+2.032*(U-128.0)

    for m in range(height):
        for n in range(width):
            if(rf[m,n]>255):
                rf[m,n]=255;
            if(gf[m,n]>255):
                gf[m,n]=255;
            if(bf[m,n]>255):
                bf[m,n]=255;

    r=rf.astype(np.uint8)
    g=gf.astype(np.uint8)
    b=bf.astype(np.uint8)
    return (r,g,b)

if __name__ == '__main__':
    width = 176
    height = 144

    yuv = readYuvFile(width, height)
    # im = Image.fromarray(yuv[0], 'L')
    # im.show()

    rgb = yuv2rgb(yuv[0], yuv[1], yuv[2], width, height)
    im_r = Image.fromarray(rgb[0], 'L')
    im_g = Image.fromarray(rgb[1], 'L')
    im_b = Image.fromarray(rgb[2], 'L')
    im_merge = Image.merge('RGB', (im_r,im_g,im_b))
    im_merge.show()

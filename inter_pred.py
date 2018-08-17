from utilities import *
import idct


def inter_pred(mb, dpb):
    luma_pred(mb, dpb)
    chroma_pred(mb, dpb)

def luma_pred(mb ,dpb):
    gen_pred_L(mb, dpb)

    for blk in mb.luma_blocks:
        idct.dec_luma4x4(blk)

def gen_pred_L(mb, dpb):

    if mb.NumMbPart != 4:
        for mbPartIdx in range(mb.NumMbPart):
            gen_pred_part_L(mb, mbPartIdx, 0, mb.MbPartWidth, mb.MbPartHeight, dpb)
    else:
        for mbPartIdx in range(4):
            s_m_t = mb.sub_mb_type[mbPartIdx]
            for subMbPartIdx in range(mb.NumSubMbPart(s_m_t)):
                gen_pred_part_L(mb, mbPartIdx, subMbPartIdx,
                                mb.SubMbPartWidth(mb.sub_mb_type[ mbPartIdx ]),
                                mb.SubMbPartHeight(mb.sub_mb_type[ mbPartIdx ]), dpb)

def gen_pred_part_L(mb, mbPartIdx, subMbPartIdx, width, height, dpb):

    ref_idx_l0 = mb.ref_idx_l0[mbPartIdx]
    refPicL0 = dpb.RefPicList0[ref_idx_l0].slice.S_prime_L

    mv_l0 = mb.mv_l0[mbPartIdx][subMbPartIdx]

    (xP, yP) = get_cord_of_mb(mb.idx, 0, mb.slice.PicWidthInSamples_L)
    xM = InverseRasterScan(mbPartIdx, mb.MbPartWidth, mb.MbPartHeight, 16, 0)
    yM = InverseRasterScan(mbPartIdx, mb.MbPartWidth, mb.MbPartHeight, 16, 1)
    xS = 0 if subMbPartIdx == 0 else InverseRasterScan(subMbPartIdx, mb.SubMbPartWidth(mb.sub_mb_type[ mbPartIdx ]),
                                                                        mb.SubMbPartHeight(mb.sub_mb_type[ mbPartIdx ]), 8, 0)
    yS = 0 if subMbPartIdx == 0 else InverseRasterScan(subMbPartIdx, mb.SubMbPartWidth(mb.sub_mb_type[ mbPartIdx ]),
                                                                        mb.SubMbPartHeight(mb.sub_mb_type[ mbPartIdx ]), 8, 1)

    xA = xP + xM + xS
    yA = yP + yM + yS

    for x in range(width):
        for y in range(height):
            xInt = xA + (mv_l0[0] >> 2) + x
            yInt = yA + (mv_l0[1] >> 2) + y
            xFrac = mv_l0[0] & 3
            yFrac = mv_l0[1] & 3
            mb.pred_L[xM + xS + x][yM + yS + y] = interpolation_L(xInt, yInt, xFrac, yFrac,
                                                                  mb.slice.PicWidthInSamples_L,
                                                                  mb.slice.PicHeightInSamples_L, refPicL0)

def interpolation_L(xInt, yInt, xFrac, yFrac, maxW, maxH, refPicL0):
    # 8.4.2.2.1
    #
    #         A   aa  B
    #
    #
    #
    #         C   bb  D
    #
    #
    #
    # E   F   G a b c H   I   J
    #         d e f g
    # cc  dd  h i j k m   ee  ff
    #         n p q r
    # K   L   M   s   N   P   Q
    #
    #
    #
    #         R   gg  S
    #
    #
    #
    #         T   hh  U
    #

    frac_table = {(0, 0):'G',
                  (0, 1):'d',
                  (0, 2):'h',
                  (0, 3):'n',
                  (1, 0):'a',
                  (1, 1):'e',
                  (1, 2):'i',
                  (1, 3):'p',
                  (2, 0):'b',
                  (2, 1):'f',
                  (2, 2):'j',
                  (2, 3):'q',
                  (3, 0):'c',
                  (3, 1):'g',
                  (3, 2):'k',
                  (3, 3):'r'}

    flag = frac_table[(xFrac, yFrac)]

    if flag == 'G':
        return luma_G(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'd':
        return luma_d(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'h':
        return luma_h(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'n':
        return luma_n(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'a':
        return luma_a(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'e':
        return luma_e(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'i':
        return luma_i(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'p':
        return luma_p(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'b':
        return luma_b(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'f':
        return luma_f(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'j':
        return luma_j(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'q':
        return luma_q(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'c':
        return luma_c(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'g':
        return luma_g(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'k':
        return luma_k(xInt, yInt, maxW, maxH, refPicL0)
    elif flag == 'r':
        return luma_r(xInt, yInt, maxW, maxH, refPicL0)

def luma_G(xInt, yInt, maxW, maxH, refPicL0):
    return refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]

def luma_h(xInt, yInt, maxW, maxH, refPicL0):
    A = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt - 2)]
    C = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt - 1)]
    G = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]
    M = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 1)]
    R = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 2)]
    T = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 3)]

    h1 = A - 5 * C + 20 * G + 20 * M - 5 * R + T
    h = Clip1_Y((h1 + 16) >> 5, 8)

    return h

def luma_d(xInt, yInt, maxW, maxH, refPicL0):
    G = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]
    h = luma_h(xInt, yInt, maxW, maxH, refPicL0)

    d = (G + h + 1) >> 1

    return d

def luma_n(xInt, yInt, maxW, maxH, refPicL0):
    M = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 1)]
    h = luma_h(xInt, yInt, maxW, maxH, refPicL0)

    n = (M + h + 1) >> 1

    return n

def luma_b(xInt, yInt, maxW, maxH, refPicL0):
    E = refPicL0[Clip3(0, maxW - 1, xInt - 2)][Clip3(0, maxH - 1, yInt)]
    F = refPicL0[Clip3(0, maxW - 1, xInt - 1)][Clip3(0, maxH - 1, yInt)]
    G = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]
    H = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt)]
    I = refPicL0[Clip3(0, maxW - 1, xInt + 2)][Clip3(0, maxH - 1, yInt)]
    J = refPicL0[Clip3(0, maxW - 1, xInt + 3)][Clip3(0, maxH - 1, yInt)]

    b1 = E - 5 * F + 20 * G + 20 * H - 5 * I + J
    b = Clip1_Y((b1 + 16) >> 5, 8)

    return b

def luma_a(xInt, yInt, maxW, maxH, refPicL0):
    G = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]
    b = luma_b(xInt, yInt, maxW, maxH, refPicL0)

    a = (G + b + 1) >> 1

    return a

def luma_c(xInt, yInt, maxW, maxH, refPicL0):
    H = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt)]
    b = luma_b(xInt, yInt, maxW, maxH, refPicL0)

    c = (H + b + 1) >> 1

    return c

def luma_s(xInt, yInt, maxW, maxH, refPicL0):
    K = refPicL0[Clip3(0, maxW - 1, xInt - 2)][Clip3(0, maxH - 1, yInt + 1)]
    L = refPicL0[Clip3(0, maxW - 1, xInt - 1)][Clip3(0, maxH - 1, yInt + 1)]
    M = refPicL0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 1)]
    N = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt + 1)]
    P = refPicL0[Clip3(0, maxW - 1, xInt + 2)][Clip3(0, maxH - 1, yInt + 1)]
    Q = refPicL0[Clip3(0, maxW - 1, xInt + 3)][Clip3(0, maxH - 1, yInt + 1)]

    s1 = K - 5 * L + 20 * M + 20 * N - 5 * P + Q
    s = Clip1_Y((s1 + 16) >> 5, 8)

    return s

def luma_m(xInt, yInt, maxW, maxH, refPicL0):
    B = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt - 2)]
    D = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt - 1)]
    H = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt)]
    N = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt + 1)]
    S = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt + 2)]
    U = refPicL0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt + 3)]

    m1 = B - 5 * D + 20 * H + 20 * N - 5 * S + U
    m = Clip1_Y((m1 + 16) >> 5, 8)

    return m

def luma_j(xInt, yInt, maxW, maxH, refPicL0):
    cc = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, -2)
    dd = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, -1)
    h1 = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, 0)
    m1 = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, 1)
    ee = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, 2)
    ff = half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, 3)

    j1 = cc - 5 * dd + 20 * h1 + 20 * m1 - 5 * ee + ff
    j = Clip1_Y((j1 + 512) >> 10, 8)

    return j

def luma_f(xInt, yInt, maxW, maxH, refPicL0):
    b = luma_b(xInt, yInt, maxW, maxH, refPicL0)
    j = luma_j(xInt, yInt, maxW, maxH, refPicL0)

    f = (b + j + 1) >> 1

    return f

def luma_i(xInt, yInt, maxW, maxH, refPicL0):
    h = luma_h(xInt, yInt, maxW, maxH, refPicL0)
    j = luma_j(xInt, yInt, maxW, maxH, refPicL0)

    i = (h + j + 1) >> 1

    return i

def luma_k(xInt, yInt, maxW, maxH, refPicL0):
    m = luma_m(xInt, yInt, maxW, maxH, refPicL0)
    j = luma_j(xInt, yInt, maxW, maxH, refPicL0)

    k = (m + j + 1) >> 1

    return k

def luma_q(xInt, yInt, maxW, maxH, refPicL0):
    s = luma_s(xInt, yInt, maxW, maxH, refPicL0)
    j = luma_j(xInt, yInt, maxW, maxH, refPicL0)

    q = (s + j + 1) >> 1

    return q

def luma_e(xInt, yInt, maxW, maxH, refPicL0):
    b = luma_b(xInt, yInt, maxW, maxH, refPicL0)
    h = luma_h(xInt, yInt, maxW, maxH, refPicL0)

    e = (b + h + 1) >> 1

    return e

def luma_g(xInt, yInt, maxW, maxH, refPicL0):
    b = luma_b(xInt, yInt, maxW, maxH, refPicL0)
    m = luma_m(xInt, yInt, maxW, maxH, refPicL0)

    g = (b + m + 1) >> 1

    return g

def luma_p(xInt, yInt, maxW, maxH, refPicL0):
    s = luma_s(xInt, yInt, maxW, maxH, refPicL0)
    h = luma_h(xInt, yInt, maxW, maxH, refPicL0)

    p = (s + h + 1) >> 1

    return p

def luma_r(xInt, yInt, maxW, maxH, refPicL0):
    s = luma_s(xInt, yInt, maxW, maxH, refPicL0)
    m = luma_m(xInt, yInt, maxW, maxH, refPicL0)

    r = (s + m + 1) >> 1

    return r

def half_pixel_ver(xInt, yInt, maxW, maxH, refPicL0, xOffset):
    Pminus2 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt - 2)]
    Pminus1 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt - 1)]
    P0 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt)]
    P1 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt + 1)]
    P2 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt + 2)]
    P3 = refPicL0[Clip3(0, maxW - 1, xInt + xOffset)][Clip3(0, maxH - 1, yInt + 3)]

    h1 = Pminus2 - 5 * Pminus1 + 20 * P0 + 20 * P1 - 5 * P2 + P3

    return h1

def chroma_pred(mb, dpb):
    for iCbCr in [1, 2]:
        gen_pred_C(mb, iCbCr, dpb)
        idct.idct_for_chroma_C(mb, iCbCr)

def gen_pred_C(mb, iCbCr, dpb):
    if iCbCr == 1:
        mb.pred_Cb = array_2d(16 // mb.slice.sps.SubWidthC, 16 // mb.slice.sps.SubHeightC, 0)
    elif iCbCr == 2:
        mb.pred_Cr = array_2d(16 // mb.slice.sps.SubWidthC, 16 // mb.slice.sps.SubHeightC, 0)

    if mb.NumMbPart != 4:
        for mbPartIdx in range(mb.NumMbPart):
            gen_pred_part_C(mb, mbPartIdx, 0, mb.MbPartWidth // mb.slice.sps.SubWidthC, mb.MbPartHeight // mb.slice.sps.SubHeightC, iCbCr, dpb)
    else:
        for mbPartIdx in range(4):
            s_m_t = mb.sub_mb_type[mbPartIdx]
            for subMbPartIdx in range(mb.NumSubMbPart(s_m_t)):
                gen_pred_part_C(mb, mbPartIdx, subMbPartIdx,
                                mb.SubMbPartWidth(mb.sub_mb_type[ mbPartIdx ]) // mb.slice.sps.SubWidthC,
                                mb.SubMbPartHeight(mb.sub_mb_type[ mbPartIdx ]) // mb.slice.sps.SubHeightC,
                                iCbCr, dpb)

def gen_pred_part_C(mb, mbPartIdx, subMbPartIdx, width, height, iCbCr, dpb):
    ref_idx_l0 = mb.ref_idx_l0[mbPartIdx]
    refPicC0 = dpb.RefPicList0[ref_idx_l0].slice.S_prime_Cb if iCbCr == 1 else dpb.RefPicList0[ref_idx_l0].slice.S_prime_Cr

    mv_l0 = mb.mv_l0[mbPartIdx][subMbPartIdx]

    (xP, yP) = get_cord_of_mb(mb.idx, 0, mb.slice.PicWidthInSamples_L)
    xM = InverseRasterScan(mbPartIdx, mb.MbPartWidth, mb.MbPartHeight, 16, 0)
    yM = InverseRasterScan(mbPartIdx, mb.MbPartWidth, mb.MbPartHeight, 16, 1)
    xS = 0 if subMbPartIdx == 0 else InverseRasterScan(subMbPartIdx, mb.SubMbPartWidth(mb.sub_mb_type[mbPartIdx]),
                                                                        mb.SubMbPartHeight(mb.sub_mb_type[mbPartIdx]), 8, 0)
    yS = 0 if subMbPartIdx == 0 else InverseRasterScan(subMbPartIdx, mb.SubMbPartWidth(mb.sub_mb_type[mbPartIdx]),
                                                                        mb.SubMbPartHeight(mb.sub_mb_type[mbPartIdx]), 8, 1)

    xA = xP + xM + xS
    yA = yP + yM + yS

    for x in range(width):
        for y in range(height):
            xInt = (xA // mb.slice.sps.SubWidthC) + (mv_l0[0] >> 3) + x
            yInt = (yA // mb.slice.sps.SubHeightC) + (mv_l0[1] >> 3) + y
            xFrac = mv_l0[0] & 7
            yFrac = mv_l0[1] & 7
            if iCbCr == 1:
                mb.pred_Cb[((xM + xS) // mb.slice.sps.SubWidthC) + x][((yM + yS) // mb.slice.sps.SubHeightC) + y] = interpolation_C(xInt, yInt, xFrac, yFrac,
                                                                                                                        mb.slice.PicWidthInSamples_C,
                                                                                                                        mb.slice.PicHeightInSamples_C,
                                                                                                                        refPicC0)
            elif iCbCr == 2:
                mb.pred_Cr[((xM + xS) // mb.slice.sps.SubWidthC) + x][((yM + yS) // mb.slice.sps.SubHeightC) + y] = interpolation_C(xInt, yInt, xFrac, yFrac,
                                                                                                                        mb.slice.PicWidthInSamples_C,
                                                                                                                        mb.slice.PicHeightInSamples_C,
                                                                                                                        refPicC0)

def interpolation_C(xInt, yInt, xFrac, yFrac, maxW, maxH, refPicC0):
    # 8.4.2.2.2
    A = refPicC0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt)]
    B = refPicC0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt)]
    C = refPicC0[Clip3(0, maxW - 1, xInt)][Clip3(0, maxH - 1, yInt + 1)]
    D = refPicC0[Clip3(0, maxW - 1, xInt + 1)][Clip3(0, maxH - 1, yInt + 1)]

    p = ((8 - xFrac) * (8 - yFrac) * A + xFrac * (8 - yFrac) * B + (8 - xFrac) * yFrac * C + xFrac * yFrac * D + 32) >> 6

    return p
from utilities import *

table_alpha = [0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,4,4,5,6,  7,8,9,10,12,13,15,17,  20,22,25,28,32,36,40,45,  50,56,63,71,80,90,101,113,  127,144,162,182,203,226,255,255]
table_beta = [0,0,0,0,0,0,0,0,0,0,0,0, 0,0,0,0,2,2,2,3,  3,3,3, 4, 4, 4, 6, 6,   7, 7, 8, 8, 9, 9,10,10,  11,11,12,12,13,13, 14, 14,   15, 15, 16, 16, 17, 17, 18, 18]
table_clip = [
  [ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],
  [ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],[ 0, 0, 0, 0, 0],
  [ 0, 0, 0, 0, 0],[ 0, 0, 0, 1, 1],[ 0, 0, 0, 1, 1],[ 0, 0, 0, 1, 1],[ 0, 0, 0, 1, 1],[ 0, 0, 1, 1, 1],[ 0, 0, 1, 1, 1],[ 0, 1, 1, 1, 1],
  [ 0, 1, 1, 1, 1],[ 0, 1, 1, 1, 1],[ 0, 1, 1, 1, 1],[ 0, 1, 1, 2, 2],[ 0, 1, 1, 2, 2],[ 0, 1, 1, 2, 2],[ 0, 1, 1, 2, 2],[ 0, 1, 2, 3, 3],
  [ 0, 1, 2, 3, 3],[ 0, 2, 2, 3, 3],[ 0, 2, 2, 4, 4],[ 0, 2, 3, 4, 4],[ 0, 2, 3, 4, 4],[ 0, 3, 3, 5, 5],[ 0, 3, 4, 6, 6],[ 0, 3, 4, 6, 6],
  [ 0, 4, 5, 7, 7],[ 0, 4, 5, 8, 8],[ 0, 4, 6, 9, 9],[ 0, 5, 7,10,10],[ 0, 6, 8,11,11],[ 0, 6, 8,13,13],[ 0, 7,10,14,14],[ 0, 8,11,16,16],
  [ 0, 9,12,18,18],[ 0,10,13,20,20],[ 0,11,15,23,23],[ 0,13,17,25,25]
]

def deblock_frame(slice):
    for mb in slice.mbs:
        deblock_mb(mb)

def deblock_mb(mb):
    '''
    8.7 Deblocking filter process
    only support h.264 baseline frame
    '''
    if mb.slice.disable_deblocking_filter_idc == 1:
        return

    (mbAddrA, blkIdxA) = mb.luma_blocks[0].luma_neighbor("A")
    (mbAddrB, blkIdxB) = mb.luma_blocks[0].luma_neighbor("B")
    mb.fieldMbInFrameFlag = 1 if mb.slice.MbaffFrameFlag == 1 and mb.mb_field_decoding_flag == 1 else 0
    mb.filterInternalEdgesFlag = 0 if mb.slice.disable_deblocking_filter_idc == 1 else 0
    if (mb.slice.MbaffFrameFlag == 0 and mb.idx % mb.slice.PicWidthInMbs == 0) or \
       (mb.slice.MbaffFrameFlag == 1 and (mb.idx >> 1) % mb.slice.PicWidthInMbs == 0) or \
       (mb.slice.disable_deblocking_filter_idc == 1) or \
       (mb.slice.disable_deblocking_filter_idc ==2 and mbAddrA == None):
        mb.filterLeftMbEdgeFlag = 0
    else:
        mb.filterLeftMbEdgeFlag = 1
    if any([
        mb.slice.MbaffFrameFlag == 0 and mb.idx < mb.slice.PicWidthInMbs,
        mb.slice.MbaffFrameFlag == 1 and (mb.idx >> 1) < mb.slice.PicWidthInMbs and mb.idx % 2 == 0,
        mb.slice.disable_deblocking_filter_idc == 1,
        mb.slice.disable_deblocking_filter_idc == 2 and mbAddrB == None
       ]):
        mb.filterTopMbEdgeFlag = 0
    else:
        mb.filterTopMbEdgeFlag = 1

    # vertical
    for edge in range(4):
        if (mb.CodedBlockPatternLuma == 0 and mb.CodedBlockPatternChroma == 0) and (mb.slice.slice_type == 'P' or mb.slice.slice_type == 'B'):
            if edge > 0:
                if (mb.mb_type == 'P_Skip' and mb.slice.slice_type == 'P') or mb.mb_type == 'P_L0_16x16' or mb.mb_type == 'P_L0_L0_16x8':
                    continue
                elif (edge & 0x01) and mb.mb_type == 'P_L0_L0_8x16':
                    continue

        if edge or mb.filterLeftMbEdgeFlag:
            strength = get_strength(mb, edge, 1)

            if sum(strength) > 0 :
                edge_loop_luma_ver(strength, mb, edge)

                if edge == 0 or edge == 2:
                    edge_loop_chroma_ver(strength, mb, edge >> 1, 0)
                    edge_loop_chroma_ver(strength, mb, edge >> 1, 1)

    # horizontal
    for edge in range(4):
        if (mb.CodedBlockPatternLuma == 0 and mb.CodedBlockPatternChroma == 0) and (mb.slice.slice_type == 'P' or mb.slice.slice_type == 'B'):
            if edge > 0:
                if (mb.mb_type == 'P_Skip' and mb.slice.slice_type == 'P') or mb.mb_type == 'P_L0_16x16' or mb.mb_type == 'P_L0_L0_8x16':
                    continue
                elif (edge & 0x01) and mb.mb_type == 'P_L0_L0_16x8':
                    continue

            if edge or mb.filterTopMbEdgeFlag:
                strength = get_strength(mb, edge, 0)

                if sum(strength) > 0:
                    edge_loop_luma_hor(strength, mb, edge)

                    if edge == 0 or edge == 2:
                        edge_loop_chroma_ver(strength, mb, edge >> 1, 0)
                        edge_loop_chroma_ver(strength, mb, edge >> 1, 1)


def get_strength(mbQ, edge, verticalEdgeFlag):
    # 8.7.2.1
    strength = [ 0 for n in range(16)]

    for i in range(4):
        if verticalEdgeFlag:
            # vertical
            blkQ = mbQ.luma_neighbor_block_location(edge << 2 , 4 * i)
            blkP = mbQ.luma_neighbor_block_location( (edge << 2) -1 , 4 * i)
        else:
            # horizontal
            blkQ = mbQ.luma_neighbor_block_location(4 * i, edge << 2)
            blkP = mbQ.luma_neighbor_block_location(4 * i, (edge << 2) - 1)
        mbP = blkP.mb

        if edge == 0:
            if mbP.is_intra() or mbQ.is_intra():
                for n in range(4):
                    strength[ ( i << 2 ) + n ] = 4
        else:
            if mbP.is_intra() or mbQ.is_intra():
                for n in range(4):
                    strength[ ( i << 2 ) + n ] = 3
            else:
                if mbQ.CodedBlockPatternLuma & ( 1 << ( blkQ.idx // 4 ) ) == 0 or mbP.CodedBlockPatternLuma & ( 1 << ( blkP.idx // 4 ) ) == 0: # maybe condition is wrong
                    for n in range(4):
                        strength[ ( i << 2 ) + n ] = 2
                else:
                    if blkP.ref_idx_l0 == blkQ.ref_idx_l0:
                        if compare_mvs(blkP.mv_l0, blkQ.mv_l0):
                            for n in range(4):
                                strength[(i << 2) + n] = 1
                    else:
                        for n in range(4):
                            strength[(i << 2) + n] = 1

    return strength

def edge_loop_luma_ver(strength, mbQ, edge):
    mbP = mbQ.luma_neighbor_block_location((edge << 2) -1, 0).mb

    if mbP == None:
        return

    BitDepth_Y = mbQ.slice.sps.BitDepth_Y

    QP = (mbP.QP_prime_Y + mbQ.QP_prime_Y + 1) >> 1

    indexA = Clip3(0, 51, QP + mbQ.slice.FilterOffsetA)
    indexB = Clip3(0, 51, QP + mbQ.slice.FilterOffsetB)

    alpha = table_alpha[indexA] * (1 << (BitDepth_Y - 8))
    beta = table_beta[indexB] * (1 << (BitDepth_Y - 8))

    if (alpha | beta) != 0:
        for i in range(16):
            dStripe = DeblockStripeY(mbQ, edge, i, 1)
            if strength[i] == 4:
                luma_deblock_strong(dStripe, alpha, beta)
            elif strength[i] > 0:
                tc0 = table_clip[indexA][strength[i]] * (1 << (BitDepth_Y - 8))
                luma_deblock_normal(dStripe, alpha,beta, tc0, BitDepth_Y)

def edge_loop_luma_hor(strength, mbQ, edge):
    mbP = mbQ.luma_neighbor_block_location(0, (edge << 2) - 1).mb

    if mbP == None:
        return

    BitDepth_Y = mbQ.slice.sps.BitDepth_Y

    QP = (mbP.QP_prime_Y + mbQ.QP_prime_Y + 1) >> 1
    
    indexA = Clip3(0, 51, QP + mbQ.slice.FilterOffsetA)
    indexB = Clip3(0, 51, QP + mbQ.slice.FilterOffsetB)

    alpha = table_alpha[indexA] * (1 << (BitDepth_Y - 8))
    beta = table_beta[indexB] * (1 << (BitDepth_Y - 8))
    
    if (alpha | beta) != 0:
        for i in range(16):
            dStripe = DeblockStripeY(mbQ, edge, i, 0)
            if strength[i] == 4:
                luma_deblock_strong(dStripe, alpha, beta)
            elif strength[i] > 0:
                tc0 = table_clip[indexA][strength[i]] * (1 << (BitDepth_Y - 8))
                luma_deblock_normal(dStripe, alpha,beta, tc0, BitDepth_Y)

def luma_deblock_strong(dStripe, alpha, beta):
    # 8.7.2.3
    p = dStripe.p
    q = dStripe.q
    (p0, p1, p2) = (p[0].v, p[1].v, p[2].v)
    (q0, q1, q2) = (q[0].v, q[1].v, q[2].v)

    if abs(p0 - q0) >= alpha or abs(p1 - p0) >= beta or abs(q1 - q0) >= beta:
        return

    # for p
    if abs(p[2].v - p[0].v) < beta and abs(p[0].v - q[0].v) < (alpha >> 2) + 2:
        p0 = (((p[1].v + p[0].v + q[0].v) << 1) + p[2].v + q[1].v + 4) >> 3
        p1 = (p[2].v + p[1].v + p[0].v + q[0].v + 2) >> 2
        p2 = (((p[3].v + p[2].v) << 1) + p[2].v + p[1].v + p[0].v + q[0].v + 4) >> 3
    else:
        p0 = ((p[1].v << 1) + p[0].v + q[1].v + 2) >> 2

    # for q
    if abs(q[2].v - q[0].v) < beta and abs(p[0].v - q[0].v) < (alpha >> 2) + 2:
        q0 = (((q[1].v + q[0].v + p[0].v) << 1) + q[2].v + p[1].v + 4) >> 3
        q1 = (q[2].v + q[1].v + q[0].v + p[0].v + 2) >> 2
        q2 = (((q[3].v + q[2].v) << 1) + q[2].v + q[1].v + q[0].v + p[0].v + 4) >> 3
    else:
        q0 = ((q[1].v << 1) + q[0].v + p[1].v + 2) >> 2

    (p[0].v, p[1].v, p[2].v) = (p0, p1, p2)
    (q[0].v, q[1].v, q[2].v) = (q0, q1, q2)
    dStripe.restore()

def luma_deblock_normal(dStripe, alpha, beta, tc0, bit_depth):
    # 8.7.2.3
    p = dStripe.p
    q = dStripe.q
    (p0, p1, p2) = (p[0].v, p[1].v, p[2].v)
    (q0, q1, q2) = (q[0].v, q[1].v, q[2].v)

    if abs(p0 - q0) >= alpha or abs(p1 - p0) >= beta or abs(q1 - q0) >= beta:
        return

    ap = abs(p[2].v - p[0].v) < beta
    aq = abs(q[2].v - q[0].v) < beta

    tc = tc0 + (1 if ap else 0) + (1 if aq else 0)

    dif = Clip3(-tc, tc, ((((q[0].v - p[0].v) << 2) + (p[1].v - q[1].v) + 4) >> 3))
    p0 = Clip1_Y(p[0].v + dif, bit_depth)
    q0 = Clip1_Y(q[0].v - dif, bit_depth)

    if ap:
        p1 = p[1].v + Clip3(-tc0, tc0, (p[2].v + ((p[0].v + q[0].v + 1) >> 1) -(p[1].v << 1)) >> 1)
    if aq:
        q1 = q[1].v + Clip3(-tc0, tc0, (q[2].v + ((p[0].v + q[0].v + 1) >> 1) - (q[1].v << 1)) >> 1)

    (p[0].v, p[1].v, p[2].v) = (p0, p1, p2)
    (q[0].v, q[1].v, q[2].v) = (q0, q1, q2)
    dStripe.restore()

def edge_loop_chroma_ver(strength, mbQ, edge, color):
    mbP = mbQ.slice.mbs[ mbQ.chroma_neighbor_location((edge << 2) -1, 0)[0] ]

    if mbP == None:
        return

    BitDepth_C = mbQ.slice.sps.BitDepth_C

    QP = (mbP.QP_prime_C + mbQ.QP_prime_C + 1) >> 1

    indexA = Clip3(0, 51, QP + mbQ.slice.FilterOffsetA)
    indexB = Clip3(0, 51, QP + mbQ.slice.FilterOffsetB)

    alpha = table_alpha[indexA] * (1 << (BitDepth_C - 8))
    beta = table_beta[indexB] * (1 << (BitDepth_C - 8))

    if (alpha | beta) != 0:
        for i in range(8):
            strng = strength[i << 1]

            if strng == 0:
                continue

            dStripe = DeblockStripeC(mbQ, edge, i, 1, color)
            p = dStripe.p
            q = dStripe.q
            (p0, p1) = (p[0].v, p[1].v)
            (q0, q1) = (q[0].v, q[1].v)

            if abs(p0 - q0) < alpha and abs(p1 - p0) < beta and abs(q1 - q0) < beta:
                if strng == 4:
                    p0 = ((p[1].v << 1) + p[0].v + q[1].v + 2) >> 2
                    q0 = ((q[1].v << 1) + q[0].v + p[1].v + 2) >> 2
                elif strng > 0:
                    tc0 = table_clip[indexA][strng] * (1 << (BitDepth_C - 8))
                    tc = tc0 + 1
                    dif = Clip3(-tc, tc, ((((q[0].v - p[0].v) << 2) + (p[1].v - q[1].v) + 4) >> 3))
                    p0 = Clip1_C(p[0].v + dif, BitDepth_C)
                    q0 = Clip1_C(q[0].v - dif, BitDepth_C)

            (p[0].v, p[1].v) = (p0, p1)
            (q[0].v, q[1].v) = (q0, q1)
            dStripe.restore()

def edge_loop_chroma_hor(strength, mbQ, edge, color):
    mbP = mbQ.slice.mbs[ mbQ.chroma_neighbor_location(0, (edge << 2) - 1)[0] ]

    if mbP == None:
        return

    BitDepth_C = mbQ.slice.sps.BitDepth_C

    QP = (mbP.QP_prime_C + mbQ.QP_prime_C + 1) >> 1

    indexA = Clip3(0, 51, QP + mbQ.slice.FilterOffsetA)
    indexB = Clip3(0, 51, QP + mbQ.slice.FilterOffsetB)

    alpha = table_alpha[indexA] * (1 << (BitDepth_C - 8))
    beta = table_beta[indexB] * (1 << (BitDepth_C - 8))

    if (alpha | beta) != 0:
        for i in range(8):
            strng = strength[i << 1]

            if strng == 0:
                continue

            dStripe = DeblockStripeC(mbQ, edge, i, 0, color)
            p = dStripe.p
            q = dStripe.q
            (p0, p1) = (p[0].v, p[1].v)
            (q0, q1) = (q[0].v, q[1].v)

            if abs(p0 - q0) < alpha and abs(p1 - p0) < beta and abs(q1 - q0) < beta:
                if strng == 4:
                    p0 = ((p[1].v << 1) + p[0].v + q[1].v + 2) >> 2
                    q0 = ((q[1].v << 1) + q[0].v + p[1].v + 2) >> 2
                elif strng > 0:
                    tc0 = table_clip[indexA][strng] * (1 << (BitDepth_C - 8))
                    tc = tc0 + 1
                    dif = Clip3(-tc, tc, ((((q[0].v - p[0].v) << 2) + (p[1].v - q[1].v) + 4) >> 3))
                    p0 = Clip1_C(p[0].v + dif, BitDepth_C)
                    q0 = Clip1_C(q[0].v - dif, BitDepth_C)

            (p[0].v, p[1].v) = (p0, p1)
            (q[0].v, q[1].v) = (q0, q1)
            dStripe.restore()

class DeblockStripeY:

    def __init__(self, mbQ, edge, pos, verticalEdgeFlag):
        self.p = [None for n in range(4)]
        self.q = [None for n in range(4)]
        self.picY = mbQ.slice.S_prime_L

        (xS, yS) = get_cord_of_mb(mbQ.idx, 0, mbQ.slice.PicWidthInSamples_L)
        if verticalEdgeFlag:
            x = xS + (edge << 2)
            y = yS + pos
            for i in range(4):
                self.p[i] = Pixel(x - 1 - i, y, self.picY[x - 1 - i][y])
                self.q[i] = Pixel(x + i, y, self.picY[x + i][y])
        else:
            x = xS + pos
            y = yS + (edge << 2)
            for i in range(4):
                self.p[i] = Pixel(x, y - 1 - i, self.picY[x][y - 1 - i])
                self.q[i] = Pixel(x, y + i, self.picY[x][y + i])

    def restore(self):
        for i in range(4):
            if self.p[i] != None:
                (x, y) = (self.p[i].x, self.p[i].y)
                self.picY[x][y] = self.p[i].v
            if self.q[i] != None:
                (x, y) = (self.q[i].x, self.q[i].y)
                self.picY[x][y] = self.q[i].v

class DeblockStripeC:

    def __init__(self, mbQ, edge, pos, verticalEdgeFlag, color):
        self.p = [None for n in range(2)]
        self.q = [None for n in range(2)]

        self.picC = mbQ.slice.S_prime_Cb if color == 0 else mbQ.slice.S_prime_Cr

        (xS, yS) = get_cord_of_mb_chroma(mbQ.idx, mbQ.slice.PicWidthInSamples_C)

        if verticalEdgeFlag:
            x = xS + (edge << 2)
            y = yS + pos
            for i in range(2):
                self.p[i] = Pixel(x - 1 - i, y, self.picC[x - 1 - i][y])
                self.q[i] = Pixel(x + i, y, self.picC[x + i][y])
        else:
            x = xS + pos
            y = yS + (edge << 2)
            for i in range(2):
                self.p[i] = Pixel(x, y - 1 - i, self.picC[x][y - 1 - i])
                self.q[i] = Pixel(x, y + i, self.picC[x][y + i])


    def restore(self):
        for i in range(2):
            if self.p[i] != None:
                (x, y) = (self.p[i].x, self.p[i].y)
                self.picC[x][y] = self.p[i].v
            if self.q[i] != None:
                (x, y) = (self.q[i].x, self.q[i].y)
                self.picC[x][y] = self.q[i].v
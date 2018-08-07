from utilities import *

table_alpha = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,4,5,6,7,8,9,10,12,13,15,17,20,22,25,28,32,36,40,45,50,56,63,71,80,90,101,113, 127,144,162,182,203,226,255,255]
table_beta = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,2,2,3,3,3,3, 4, 4, 4, 6, 6, 7, 7, 8, 8, 9, 9,10,10, 11,11,12,12,13,13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18]

def deblock_frame(slice):
    for mb in slice.mbs:
        deblock_mb(mb)

def deblock_mb(mb):
    '''
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

    for edge in range(4):
        if (mb.CodedBlockPatternLuma == 0 and mb.CodedBlockPatternChroma == 0) and (mb.slice.slice_type == 'P' and mb.slice.slice_type == 'B'):
            #TODO
            raise NameError('deblock not impl')

        if edge or mb.filterLeftMbEdgeFlag:
            strength = get_strength(mb, edge)



def get_strength(mbQ, edge_x):
    slice = mbQ.slice
    if slice.slice_type == 'SI' or slice.slice_type == 'SP':
        raise NameError('deblock SI or SP slice not impl')
    else:
        (mbAddrTmp, xW, yW) = self.mb.luma_neighbor_location(edge_x, 0)
        mbP = slice.mbs[mbAddrTmp]
        for idx in range(0, 16, 4):


def deblock_blk(blk):
    pass

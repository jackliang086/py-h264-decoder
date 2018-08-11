from block import Block
from pprint import pprint
from utilities import array_2d, Clip3, InverseRasterScan, median_mv, add_mv, is_zero_mv

mbtype_islice_table = ["I_NxN","I_16x16_0_0_0","I_16x16_1_0_0","I_16x16_2_0_0","I_16x16_3_0_0","I_16x16_0_1_0","I_16x16_1_1_0","I_16x16_2_1_0","I_16x16_3_1_0","I_16x16_0_2_0","I_16x16_1_2_0","I_16x16_2_2_0","I_16x16_3_2_0","I_16x16_0_0_1","I_16x16_1_0_1","I_16x16_2_0_1","I_16x16_3_0_1","I_16x16_0_1_1","I_16x16_1_1_1","I_16x16_2_1_1","I_16x16_3_1_1","I_16x16_0_2_1","I_16x16_1_2_1","I_16x16_2_2_1","I_16x16_3_2_1","I_PCM"]
mbtype_pslice_table = ["P_L0_16x16", "P_L0_L0_16x8", "P_L0_L0_8x16", "P_8x8", "P_8x8ref0", "P_Skip"]

sub_mb_type_pslice_table = ['P_L0_8x8', 'P_L0_8x4', 'P_L0_4x8', 'P_L0_4x4']

class Macroblock:

    def __init__(self, parent_slice, idx, pskip = False):
        self.idx = idx
        self.slice = parent_slice
        self.params = {}
        self.var = {}
        if pskip:
            self.mb_type_int = 5
            self.mb_type = 'P_Skip'
        else:
            self.mb_type_int = self.slice.bits.ue()
        if self.slice.slice_type == "I":
            self.mb_type = mbtype_islice_table[self.mb_type_int]
        elif self.slice.slice_type == "P":
            if not pskip:
                if self.mb_type_int > 4:
                    self.mb_type = mbtype_islice_table[self.mb_type_int - 5]
                else:
                    self.mb_type = mbtype_pslice_table[self.mb_type_int]
            print(str(self.idx) + ' ' + self.mb_type)
        else:
            raise NameError("Unknow MB Type")
        self.pred_mode = self.MbPartPredMode(self.mb_type_int)
        self.luma_blocks = []
        if self.pred_mode == 'Intra_4x4':
            for i in range(16):
                self.luma_blocks.append(Block(i, self, "Y", "4x4"))
        elif self.pred_mode == 'Intra_8x8':
            for i in range(4):
                self.luma_blocks.append(Block(i, self, "Y", "8x8"))
        elif self.pred_mode == 'Intra_16x16':
            self.luma_i16x16_dc_block = Block(0, self, "Y", "16x16", "DC")
            for i in range(16):
                self.luma_blocks.append(Block(i, self, "Y", "16x16", "AC"))
        else:
            self.ref_idx_l0 = []
            self.ref_idx_l1 = []
            for i in range(self.NumMbPart):
                self.ref_idx_l0.append(0)
                self.ref_idx_l1.append(0)
            for i in range(16):
                self.luma_blocks.append(Block(i, self, 'Y', '4x4'))

        self.chroma_dc_blocks = [Block(0, self, "Cb", "", "DC"),
                                 Block(1, self, "Cr", "", "DC")]
        self.chroma_ac_blocks = [None, None]
        for i in range(2):
            self.chroma_ac_blocks[i] = []
            for j in range(4):
                color = "Cb" if i == 0 else "Cr"
                blk = Block(j, self, color,None, "AC")
                self.chroma_ac_blocks[i].append(blk)
        # self.luma_i16x16_ac_block = []
        # if "16x16" in self.mb_type:
        #     for i in range(16):
        #         self.luma_i16x16_ac_block.append(Block(i, "Intra16x16ACLevel", self))

    def parse(self):
        # print("  MacroBlock ", self.addr, " Decoding...")
        if self.mb_type != 'P_Skip':
            self.init_params()
            self.macroblock_layer()

        if self.slice.slice_type == 'P':
            self.calculate_mv()

    def init_params(self):
        self.transform_size_8x8_flag = 0
        self.prev_intra4x4_pred_mode_flag = [None]*16
        self.prev_intra8x8_pred_mode_flag = [None]*16
        self.rem_intra4x4_pred_mode = [None]*16
        self.rem_intra8x8_pred_mode = [None]*16
        self.pred_L = array_2d(16,16)

    def macroblock_layer(self) :
        # TODO I_PCM
        if self.mb_type == 'I_PCM':
            raise NameError('I_PCM not impl')
        else:
            noSubMbPartSizeLessThan8x8Flag = 1
            if self.mb_type != 'I_NxN' and self.pred_mode != 'Intra_16x16' and self.NumMbPart == 4:
                self.sub_mb_pred()
                for mbPartIdx in range(4):
                    if self.sub_mb_type[mbPartIdx] != 'B_Direct_8x8':
                        if self.NumSubMbPart(self.sub_mb_type[mbPartIdx]) > 1:
                            noSubMbPartSizeLessThan8x8Flag = 0
                        elif not self.slice.sps.direct_8x8_inference_flag:
                            noSubMbPartSizeLessThan8x8Flag = 0
            else:
                if self.slice.pps.transform_8x8_mode_flag and self.mb_type == 'I_NxN':
                    self.transform_size_8x8_flag = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.u(1)
                self.mb_pred()
            if self.pred_mode != 'Intra_16x16' :
                self.coded_block_pattern = self.slice.bits.me(self.pred_mode, self.slice.sps.ChromaArrayType)
                self.CodedBlockPatternLuma = self.coded_block_pattern % 16
                self.CodedBlockPatternChroma = self.coded_block_pattern // 16
            if self.CodedBlockPatternLuma > 0 or self.CodedBlockPatternChroma > 0 or \
               self.pred_mode == 'Intra_16x16' :
                self.mb_qp_delta = self.slice.bits.se()

                if self.idx == 0:
                    SliceQP_Y = 26 + self.slice.pps.pic_init_qp_minus26 + self.slice.slice_qp_delta
                    QP_YPREV = SliceQP_Y
                else:
                    QP_YPREV = self.slice.mbs[self.idx - 1].QP_Y
                QpBdOffset_Y = self.slice.sps.QpBdOffset_Y
                self.QP_Y = ( ( QP_YPREV + self.mb_qp_delta + 52 + 2 * QpBdOffset_Y ) % (52 + QpBdOffset_Y)) - QpBdOffset_Y
                self.QP_prime_Y = self.QP_Y + QpBdOffset_Y
                if self.slice.sps.qpprime_y_zero_transform_bypass_flag == 1 and self.QP_prime_Y == 0:
                    self.TransformBypassModeFlag = 1
                else:
                    self.TransformBypassModeFlag = 0

                table_8_15 = [29,30,31,32,32,33,34,34,35,35,36,36,37,37,37,38,38,38,39,39,39,39]
                # Cb
                qP_Offset = self.slice.pps.chroma_qp_index_offset
                qP_I = Clip3(-self.slice.sps.QpBdOffset_C, 51, self.QP_Y + qP_Offset)
                self.QP_C = qP_I if qP_I < 30 else table_8_15[qP_I - 30]
                self.QP_prime_C = self.QP_C + self.slice.sps.QpBdOffset_C

                self.residual(0, 15)


    def mb_pred(self):
        if self.pred_mode == 'Intra_4x4' or \
           self.pred_mode == 'Intra_8x8' or \
           self.pred_mode == 'Intra_16x16':
            if self.pred_mode == 'Intra_4x4':
                for luma4x4BlkIdx in range(16):
                    self.luma_blocks[luma4x4BlkIdx].prev_intra4x4_pred_mode_flag = self.slice.bits.u(1)
                    if not self.luma_blocks[luma4x4BlkIdx].prev_intra4x4_pred_mode_flag:
                        self.luma_blocks[luma4x4BlkIdx].rem_intra4x4_pred_mode = self.slice.bits.u(3)
                    # print("rev_pred_mode_flag:", self.luma_blocks[luma4x4BlkIdx].prev_intra4x4_pred_mode_flag)
            if self.pred_mode == 'Intra_8x8':
                raise NameError("I8x8 not Impl")
            if self.slice.sps.ChromaArrayType == 1 or self.slice.sps.ChromaArrayType == 2:
                self.intra_chroma_pred_mode = self.slice.bits.ue()
        elif self.pred_mode != "Direct":
            # init mvd
            self.mvd_l0 = []
            self.mvd_l1 = []
            for mbPartIdx in range(self.NumMbPart):
                self.mvd_l0.append([[0, 0]])
                self.mvd_l1.append([[0, 0]])

            for mbPartIdx in range(self.NumMbPart):
                if ( self.slice.num_ref_idx_l0_active_minus1 > 0 or \
                     self.slice.mb_field_decoding_flag != self.slice.field_pic_flag ) and self.pred_mode != 'Pred_L1':
                    self.ref_idx_l0[mbPartIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.te(self.slice.num_ref_idx_l0_active_minus1)
            for mbPartIdx in range(self.NumMbPart):
                if ( self.slice.num_ref_idx_l1_active_minus1 > 0 or \
                     self.slice.mb_field_decoding_flag != self.slice.field_pic_flag ) and self.pred_mode != 'Pred_L0':
                    self.ref_idx_l1[mbPartIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.te(self.slice.num_ref_idx_l1_active_minus1)
            for mbPartIdx in range(self.NumMbPart):
                if self.pred_mode != 'Pred_L1':
                    for compIdx in range(2):
                        self.mvd_l0[mbPartIdx][0][compIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.se()
            for mbPartIdx in range(self.NumMbPart):
                if self.pred_mode != 'Pred_L0':
                    for compIdx in range(2):
                        self.mvd_l1[mbPartIdx][0][compIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.se()

    def sub_mb_pred(self):
        self.sub_mb_type = [None] * 4
        for mbPartIdx in range(4):
            self.sub_mb_type[mbPartIdx] = sub_mb_type_pslice_table[self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.ue()]

        # init mvd
        self.mvd_l0 = [None for n in range(4)]
        self.mvd_l1 = [None for n in range(4)]
        self.mvp_l0 = [None for n in range(4)]
        for mbPartIdx in range(4):
            self.mvd_l0[mbPartIdx] = [ [0, 0] for n in range(self.NumSubMbPart(self.sub_mb_type[mbPartIdx]))]
            self.mvp_l0[mbPartIdx] = [ [0, 0] for n in range(self.NumSubMbPart(self.sub_mb_type[mbPartIdx]))]

        for mbPartIdx in range(4):
            if ( self.slice.num_ref_idx_l0_active_minus1 > 0 or \
                 self.slice.mb_field_decoding_flag != self.slice.field_pic_flag ) and \
                 self.mb_type != 'P_8x8ref0' and self.sub_mb_type[mbPartIdx] != 'B_Direct_8x8' and self.SubMbPredMode(self.sub_mb_type[mbPartIdx]) != 'Pred_L1':
                self.ref_idx_l0[mbPartIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.te(self.slice.num_ref_idx_l0_active_minus1)
        for mbPartIdx in range(4):
            if ( self.slice.num_ref_idx_l1_active_minus1 > 0 or \
                 self.slice.mb_field_decoding_flag != self.slice.field_pic_flag ) and \
                 self.mb_type != 'P_8x8ref0' and self.sub_mb_type[mbPartIdx] != 'B_Direct_8x8' and self.SubMbPredMode(self.sub_mb_type[mbPartIdx]) != 'Pred_L0':
                self.ref_idx_l1[mbPartIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.te(self.slice.num_ref_idx_l1_active_minus1)
        for mbPartIdx in range(4):
            if self.sub_mb_type[mbPartIdx] != 'B_Direct_8x8' and self.SubMbPredMode(self.sub_mb_type[mbPartIdx]) != 'Pred_L1':
                for subMbPartIdx in range(self.NumSubMbPart(self.sub_mb_type[mbPartIdx])):
                    for compIdx in range(2):
                        self.mvd_l0[mbPartIdx][subMbPartIdx][compIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.se()
        for mbPartIdx in range(4):
            if self.sub_mb_type[mbPartIdx] != 'B_Direct_8x8' and self.SubMbPredMode(self.sub_mb_type[mbPartIdx]) != 'Pred_L0':
                for subMbPartIdx in range(self.NumSubMbPart(self.sub_mb_type[mbPartIdx])):
                    for compIdx in range(2):
                        self.mvd_l1[mbPartIdx][subMbPartIdx][compIdx] = self.slice.bits.ae() if self.slice.pps.entropy_coding_mode_flag else self.slice.bits.se()


    def residual(self, startIdx, endIdx):
        self.residual_luma(startIdx, endIdx)
        if self.slice.sps.ChromaArrayType == 1 or self.slice.sps.ChromaArrayType == 2:
            NumC8x8 = 4 // (self.slice.sps.SubWidthC * self.slice.sps.SubHeightC)
            for iCbCr in range(2):
                if self.CodedBlockPatternChroma & 3 and startIdx == 0:
                    self.chroma_dc_blocks[iCbCr].parse(0,4 * NumC8x8 - 1, 4 * NumC8x8)
                else:
                    self.chroma_dc_blocks[iCbCr].coeffLevel = [0] * (4 * NumC8x8)
            for iCbCr in range(2):
                for i8x8 in range(NumC8x8):
                    for i4x4 in range(4):
                        if self.CodedBlockPatternChroma & 2:
                            self.chroma_ac_blocks[iCbCr][i8x8*4+i4x4].parse(max(0, startIdx-1), endIdx-1, 15)
                        else:
                            self.chroma_ac_blocks[iCbCr][i8x8*4+i4x4].coeffLevel = [0] * 16
        elif self.slice.sps.ChromaArrayType == 3:
            raise NameError("ChromaArrayType == 3 not impl")

    def residual_luma(self, startIdx, endIdx):
        if startIdx == 0 and \
           self.pred_mode == 'Intra_16x16':
            self.luma_i16x16_dc_block.parse(0, 15, 16)
        for i8x8 in range(4):
            for i4x4 in range(4):
                if self.CodedBlockPatternLuma & (1 << i8x8):
                    if self.pred_mode == 'Intra_16x16':
                        # raise NameError("i16x16 not impl")
                        self.luma_blocks[i8x8 * 4 + i4x4].parse(max(0, startIdx - 1), endIdx - 1, 15)
                        # self.residual_block(self.i16x16AClevel[i8x8 * 4 + i4x4], max(0, startIdx - 1), endIdx - 1, 15, "Intra16x16ACLevel")
                    else:
                        self.luma_blocks[i8x8 * 4 + i4x4].color = "Y"
                        self.luma_blocks[i8x8 * 4 + i4x4].size = "4x4"
                        self.luma_blocks[i8x8 * 4 + i4x4].parse(startIdx, endIdx, 16)
                elif self.pred_mode == 'Intra_16x16':
                    # raise NameError("i16x16 not impl")
                    self.luma_blocks[i8x8 * 4 + i4x4].coeffLevel = [0]*15
                else:
                    self.luma_blocks[i8x8 * 4 + i4x4].coeffLevel = [0] * 16
                if not self.slice.pps.entropy_coding_mode_flag and \
                   self.transform_size_8x8_flag:
                    raise NameError("mb 123")
                    for i in range(16):
                        self.level8x8[ i8x8 ][ 4 * i + i4x4 ] = self.level4x4[ i8x8 * 4 + i4x4 ][ i ]

    def MbPartPredMode(self, mb_type_int, n = 0):
        self.NumMbPart = 1
        if self.slice.slice_type == 'I':
            if mb_type_int == 0:
                return 'Intra_4x4'
            elif mb_type_int >= 1 and mb_type_int <= 24:
                self.Intra16x16PredMode = (mb_type_int - 1) % 4
                self.CodedBlockPatternChroma = ((mb_type_int - 1) // 4) % 3
                self.CodedBlockPatternLuma = (mb_type_int // 13) * 15
                return 'Intra_16x16'
            else:
                raise NameError("Unknown MbPartPredMode")
        elif self.slice.slice_type == 'P':
            if self.mb_type == 'P_Skip':
                self.NumMbPart = 1
                self.MbPartWidth = 16
                self.MbPartHeight = 16
                return 'Pred_L0'

            if mb_type_int > 4:
                mb_type_int_minus5 = mb_type_int - 5
                if mb_type_int_minus5 == 0:
                    return 'Intra_4x4'
                elif mb_type_int_minus5 >= 1 and mb_type_int_minus5 <= 24:
                    self.Intra16x16PredMode = (mb_type_int_minus5 - 1) % 4
                    self.CodedBlockPatternChroma = ((mb_type_int_minus5 - 1) // 4) % 3
                    self.CodedBlockPatternLuma = (mb_type_int_minus5 // 13) * 15
                    return 'Intra_16x16'
                else:
                    raise NameError("Unknown MbPartPredMode")
            elif (mb_type_int, n) in [(0,0), (1,0), (2,0), (5,0), (1,1), (2,1)]:
                self.NumMbPart = [1,2,2,4,4,1][mb_type_int]
                self.MbPartWidth = [16,16,8,8,8,16][mb_type_int]
                self.MbPartHeight = [16,8,16,8,8,16][mb_type_int]
                return "Pred_L0"
            elif mb_type_int in [3, 4]:
                self.NumMbPart = 4
                self.MbPartWidth = 8
                self.MbPartHeight = 8
                return 'na'

    def SubMbPredMode(self, sub_mb_type):
        return 'Pred_L0'

    def NumSubMbPart(self, sub_mb_type):
        if sub_mb_type == 'P_L0_8x8':
            return 1
        elif sub_mb_type == 'P_L0_8x4' or sub_mb_type == 'P_L0_4x8':
            return 2
        elif sub_mb_type == 'P_L0_4x4':
            return 4

    def SubMbPartWidth(self, sub_mb_type):
        if sub_mb_type == 'P_L0_8x8' or sub_mb_type == 'P_L0_8x4':
            return 8
        elif sub_mb_type == 'P_L0_4x8' or sub_mb_type == 'P_L0_4x4':
            return 4

    def SubMbPartHeight(self, sub_mb_type):
        if sub_mb_type == 'P_L0_8x8' or sub_mb_type == 'P_L0_4x8':
            return 8
        elif sub_mb_type == 'P_L0_8x4' or sub_mb_type == 'P_L0_4x4':
            return 4

    def is_intra(self):
        return True if 'Intra' in self.pred_mode else False

    def calculate_mv(self):
        if self.is_intra():
            return

        if self.mb_type == 'P_Skip':
            self.mvd_l0 = [[[0, 0]]]


        if self.NumMbPart == 2:
            for mbPartIdx in range(2):
                (neighbor_a, neighbor_b, neighbor_c) = self.get_mvp_neighbor(mbPartIdx, 0)
                ref_idx = self.ref_idx_l0[mbPartIdx]
                mv_pred = self.get_mvp_normal(ref_idx, neighbor_a, neighbor_b, neighbor_c, mbPartIdx)
                mv = add_mv(self.mvd_l0[mbPartIdx][0], mv_pred)
                if self.MbPartWidth == 16:
                    # width = 16 height = 8
                    self.set_mv(0, self.MbPartHeight * mbPartIdx, self.MbPartWidth, self.MbPartHeight, mv, ref_idx)
                else:
                    # width = 8 height = 16
                    self.set_mv(self.MbPartWidth * mbPartIdx, 0, self.MbPartWidth, self.MbPartHeight, mv, ref_idx)
                print('mbIdx:{} mbPartIdx:{} mvd:{} mv:{}'.format(self.idx, mbPartIdx, self.mvd_l0[mbPartIdx][0], mv))
        else:
            if self.NumMbPart == 1:
                (neighbor_a, neighbor_b, neighbor_c) = self.get_mvp_neighbor(0, 0)

                zero_mv_a = True if neighbor_a == None or (neighbor_a.ref_idx_l0 == 0 and is_zero_mv(neighbor_a.mv_l0)) else False
                zero_mv_b = True if neighbor_b == None or (neighbor_b.ref_idx_l0 == 0 and is_zero_mv(neighbor_b.mv_l0)) else False
                if self.mb_type == 'P_Skip' and ( zero_mv_a or zero_mv_b ):
                    # 8.4.1.1 Derivation process for luma motion vectors for skipped macroblocks in P and SP slices
                    self.set_mv(0, 0, self.MbPartWidth, self.MbPartHeight, [0, 0], 0)
                    print('skip mbIdx:{} mvd:{} mv:{}'.format(self.idx, self.mvd_l0[0][0], [0, 0]))
                    return

                ref_idx = self.ref_idx_l0[0]
                mv_pred = self.get_mvp_normal(ref_idx, neighbor_a, neighbor_b, neighbor_c)
                mv = add_mv(self.mvd_l0[0][0], mv_pred)
                self.set_mv(0, 0, self.MbPartWidth, self.MbPartHeight, mv, ref_idx)
                print('mbIdx:{} mvd:{} mv:{}'.format(self.idx, self.mvd_l0[0][0], mv))
            else:
                # P_8x8 P_8x8ref0
                for mbPartIdx in range(4):
                    s_m_t = self.sub_mb_type[mbPartIdx]
                    for subMbPartIdx in range(self.NumSubMbPart(s_m_t)):
                        (neighbor_a, neighbor_b, neighbor_c) = self.get_mvp_neighbor(mbPartIdx, subMbPartIdx)
                        ref_idx = self.ref_idx_l0[mbPartIdx]
                        mv_pred = self.get_mvp_normal(ref_idx, neighbor_a, neighbor_b, neighbor_c)
                        mv = add_mv(self.mvd_l0[mbPartIdx][subMbPartIdx], mv_pred)

                        x = InverseRasterScan(mbPartIdx, self.MbPartWidth, self.MbPartHeight, 16, 0)
                        y = InverseRasterScan(mbPartIdx, self.MbPartWidth, self.MbPartHeight, 16, 1)
                        xS = InverseRasterScan(subMbPartIdx, self.SubMbPartWidth(s_m_t),
                                               self.SubMbPartHeight(s_m_t), 8, 0)
                        yS = InverseRasterScan(subMbPartIdx, self.SubMbPartWidth(s_m_t),
                                               self.SubMbPartHeight(s_m_t), 8, 1)
                        s_x = x + xS
                        s_y = y + yS
                        self.set_mv(s_x, s_y, self.SubMbPartWidth(s_m_t), self.SubMbPartHeight(s_m_t), mv, ref_idx)
                        print('mbIdx:{} mbPartIdx{} subMbPartIdx{} mvd:{} mv:{}'.format(self.idx, mbPartIdx, subMbPartIdx, self.mvd_l0[0][0], mv))



    def set_mv(self, x, y, width, height, mv_l0, ref_idx_l0):
        for h in range(0, height, 4):
            for w in range(0, width, 4):
                xW = x + w
                yW = y + h
                luma4x4BlkIdxTmp = int(8 * ( yW // 8 ) + 4 * ( xW // 8 ) + 2 * ( ( yW % 8 ) // 4 ) + ( ( xW % 8 ) // 4 ))
                blk = self.luma_blocks[luma4x4BlkIdxTmp]
                blk.mv_l0 = mv_l0
                blk.ref_idx_l0 = ref_idx_l0

    def get_mvp_normal(self, ref_idx, neighborA, neighborB, neighborC, partIdx=-1):
        mv_pred_type = 'M'

        ref_a = -1 if neighborA == None else neighborA.ref_idx_l0
        ref_b = -1 if neighborB == None else neighborB.ref_idx_l0
        ref_c = -1 if neighborC == None else neighborC.ref_idx_l0

        # Prediction if only one of the neighbors uses the reference frame we are checking
        if ref_a == ref_idx and ref_b != ref_idx and ref_c != ref_idx:
            mv_pred_type = 'L'
        elif ref_a != ref_idx and ref_b == ref_idx and ref_c != ref_idx:
            mv_pred_type = 'U'
        elif ref_a != ref_idx and ref_b != ref_idx and ref_c == ref_idx:
            mv_pred_type = 'UR'

        # Directional predictions
        if self.MbPartWidth == 16 and self.MbPartHeight == 8:
            if partIdx == 0:
                if ref_idx == ref_b:
                    mv_pred_type = 'U'
            elif partIdx == 1:
                if ref_idx == ref_a:
                    mv_pred_type = 'L'
        elif self.MbPartWidth == 8 and self.MbPartHeight == 16:
            if partIdx == 0:
                if ref_idx == ref_a:
                    mv_pred_type = 'L'
            elif partIdx == 1:
                if ref_idx == ref_c:
                    mv_pred_type = 'UR'

        pmv = [0, 0]
        if mv_pred_type == 'M':
            if not (neighborB != None or neighborC != None):
                if neighborA != None:
                    pmv = neighborA.mv_l0
            else:
                mv_a = [0, 0] if neighborA == None else neighborA.mv_l0
                mv_b = [0, 0] if neighborB == None else neighborB.mv_l0
                mv_c = [0, 0] if neighborC == None else neighborC.mv_l0

                pmv = median_mv(mv_a ,mv_b, mv_c)
        elif mv_pred_type == 'L':
            if neighborA != None:
                pmv = neighborA.mv_l0
        elif mv_pred_type == 'U':
            if neighborB != None:
                pmv = neighborB.mv_l0
        elif mv_pred_type == 'UR':
            if neighborC != None:
                pmv = neighborC.mv_l0

        return pmv

    def get_mvp_neighbor_2parts(self):
        neighbor_a = self.luma_neighbor_block_location(-1, 0)
        neighbor_b = self.luma_neighbor_block_location(0, -1)
        neighbor_c = self.luma_neighbor_block_location(16, -1)

        if neighbor_c == None:
            neighbor_d = self.luma_neighbor_block_location(-1, -1)
            neighbor_c = neighbor_d

        return (neighbor_a, neighbor_b, neighbor_c)

    def get_mvp_neighbor(self, mbPartIdx, subMbPartIdx):
        neighbor_a = self.luma_neighbor_partition_location(mbPartIdx, subMbPartIdx, 'A')
        neighbor_b = self.luma_neighbor_partition_location(mbPartIdx, subMbPartIdx, 'B')
        neighbor_c = self.luma_neighbor_partition_location(mbPartIdx, subMbPartIdx, 'C')

        if neighbor_c == None:
            neighbor_d = self.luma_neighbor_partition_location(mbPartIdx, subMbPartIdx, 'D')
            neighbor_c = neighbor_d

        return (neighbor_a, neighbor_b, neighbor_c)

    def luma_neighbor_partition_location(self, mbPartIdx, subMbPartIdx, direct):
        # 6.4.11.7
        x = InverseRasterScan( mbPartIdx, self.MbPartWidth, self.MbPartHeight, 16, 0 )
        y = InverseRasterScan( mbPartIdx, self.MbPartWidth, self.MbPartHeight, 16, 1 )

        if self.mb_type == 'P_8x8' or self.mb_type == 'P_8x8ref0' or self.mb_type == 'B_8x8':
            xS = InverseRasterScan( subMbPartIdx, self.SubMbPartWidth( self.sub_mb_type[ mbPartIdx ] ), self.SubMbPartHeight( self.sub_mb_type[ mbPartIdx ] ), 8, 0 )
            yS = InverseRasterScan( subMbPartIdx, self.SubMbPartWidth( self.sub_mb_type[ mbPartIdx ] ), self.SubMbPartHeight( self.sub_mb_type[ mbPartIdx ] ), 8, 1 )
        else:
            xS = 0
            yS = 0

        if self.mb_type == 'P_Skip':
            predPartWidth = 16
        elif self.mb_type == 'P_8x8' or self.mb_type == 'P_8x8ref0':
            predPartWidth = self.SubMbPartWidth(self.sub_mb_type[mbPartIdx])
        else:
            predPartWidth = self.MbPartWidth

        shiftTable = {'A':(-1,0), 'B':(0,-1), 'C':(predPartWidth,-1), 'D':(-1,-1)}
        (xD, yD) = shiftTable[direct]

        xN = x + xS + xD
        yN = y + yS + yD

        (mbAddrTmp, xW, yW) = self.luma_neighbor_location(xN, yN)
        if mbAddrTmp == None:
            luma4x4BlkIdxTmp = None
        else:
            luma4x4BlkIdxTmp = int(8 * ( yW // 8 ) + 4 * ( xW // 8 ) + 2 * ( ( yW % 8 ) // 4 ) + ( ( xW % 8 ) // 4 ))
        # print("      Find neighbor:", direct)
        # print("      xD, yD:", xD, yD)
        # print("      x, y:", x, y)
        # print("      xN, yN:", xN, yN)
        # print("      xW, yW:", xW, yW)
        # print("      mbAddrN:", mbAddrTmp)
        # print("      lumaIdx:", luma4x4BlkIdxTmp)
        # print("  -> MB:", mbAddrTmp, "BLK:", luma4x4BlkIdxTmp)
        if mbAddrTmp == None:
            return None
        else:
            mb = self.slice.mbs[mbAddrTmp]
            blk = mb.luma_blocks[luma4x4BlkIdxTmp]
            if mb.is_intra():
                blk.ref_idx_l0 = -1
                blk.mv_l0 = [0, 0]
            return blk

    def luma_neighbor_block_location(self, xN, yN):
        (mbAddrTmp, xW, yW) = self.luma_neighbor_location(xN, yN)
        if mbAddrTmp == None:
            luma4x4BlkIdxTmp = None
        else:
            luma4x4BlkIdxTmp = int(8 * ( yW // 8 ) + 4 * ( xW // 8 ) + 2 * ( ( yW % 8 ) // 4 ) + ( ( xW % 8 ) // 4 ))

        if mbAddrTmp == None:
            return None
        else:
            mb = self.slice.mbs[mbAddrTmp]
            blk = mb.luma_blocks[luma4x4BlkIdxTmp]
            if mb.is_intra():
                blk.ref_idx_l0 = -1
                blk.mv_l0 = [0, 0]
            return blk

    def luma_neighbor_location(self, xN, yN):
        # 6.4.12
        maxW = 16
        maxH = 16
        if self.slice.MbaffFrameFlag == 0:
            # 6.4.12.1
            tmp = self.belongMB(xN, yN, maxW, maxH)
            if tmp == "A":
                mbAddrTmp = self.idx - 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or self.idx % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            elif tmp == "B":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs
                if mbAddrTmp < 0 or mbAddrTmp > self.idx:
                    mbAddrTmp = None
            elif tmp == "X":
                mbAddrTmp = self.idx
            elif tmp == "C":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs + 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or ( self.idx + 1 ) % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            elif tmp == "D":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs - 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or self.idx % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            else:
                mbAddrTmp = None
            xW = ( xN + maxW ) % maxW
            yW = ( yN + maxH ) % maxH
        else:
            # 6.4.12.2
            raise NameError("6.4.12.2 not impl")
        return (mbAddrTmp, xW, yW)

    def chroma_neighbor_location(self, xN, yN):
        maxW = self.slice.sps.MbWidthC
        maxH = self.slice.sps.MbHeightC
        if self.slice.MbaffFrameFlag == 0:
            tmp = self.belongMB(xN, yN, maxW, maxH)
            if tmp == "A":
                mbAddrTmp = self.idx - 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or self.idx % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            elif tmp == "B":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs
                if mbAddrTmp < 0 or mbAddrTmp > self.idx:
                    mbAddrTmp = None
            elif tmp == "X":
                mbAddrTmp = self.idx
            elif tmp == "C":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs + 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or (self.idx + 1) % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            elif tmp == "D":
                mbAddrTmp = self.idx - self.slice.PicWidthInMbs - 1
                if mbAddrTmp < 0 or mbAddrTmp > self.idx or self.idx % self.slice.PicWidthInMbs == 0:
                    mbAddrTmp = None
            else:
                raise NameError("direction impossible")
            xW = ( xN + maxW ) % maxW
            yW = ( yN + maxH ) % maxH
        else:
            # 6.4.12.2
            raise NameError("6.4.12.2 not impl")
        return (mbAddrTmp, xW, yW)

    def belongMB(self, xN, yN, maxW, maxH):
        # find the mb which neighbour belongs to
        if xN < 0 and yN < 0:
            return "D"
        if xN < 0 and (0 <= yN and yN <= maxH-1):
            return "A"
        if (0 <= xN and xN <= maxW-1) and yN < 0:
            return "B"
        if (0 <= xN and xN <= maxW-1) and (0 <= yN and yN <= maxH-1):
            return "X"
        if xN > maxW - 1 and yN < 0:
            return "C"
        if xN > maxW - 1 and (0 <= yN and yN <= maxH-1):
            return None
        if yN > maxH-1:
            return None

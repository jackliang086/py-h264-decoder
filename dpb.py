'''
decode picture buffer only support baseline frame now
'''

class DPB:
    # 8.2.4
    def __init__(self, vps):

        self.FrameList = []

        self.refFrameList0ShortTerm = []
        self.refFrameList0LongTerm = []

        self.RefPicList0 = []

        self.vps = vps

    def init_pic_list(self, slice):
        # 8.2.4.2
        for f in self.refFrameList0ShortTerm:
            if f.FrameNum > slice.frame_num:
                f.FrameNumWrap = f.FrameNum - self.vps.max_frame_num
            else:
                f.FrameNumWrap = f.FrameNum
            f.PicNum = f.FrameNumWrap

        for f in self.refFrameList0LongTerm:
            f.LongTermPicNum = f.LongTermFrameIdx

        self.RefPicList0.clear()

        if slice.slice_type == 'I':
            return

        self.refFrameList0ShortTerm.sort(key=lambda f: f.PicNum, reverse=True)
        for f in self.refFrameList0ShortTerm:
            self.RefPicList0.append(f)

        self.refFrameList0LongTerm.sort(key=lambda f: f.LongTermPicNum, reverse=False)
        for f in self.refFrameList0LongTerm:
            self.RefPicList0.append(f)

        if len(self.RefPicList0) > slice.pps.num_ref_idx_l0_default_active_minus1 + 1:
            self.RefPicList0 = self.RefPicList0[:slice.pps.num_ref_idx_l0_default_active_minus1 + 1]

    def ref_pic_list_reordering(self, slice):
        # 8.2.4.3
        if slice.slice_type == 'P' and slice.ref_pic_list_modification_flag_l0 == 1:
            # TODO
            pass

    def store_pic_in_dpb(self, slice):
        # 8.2.5
        fs = FrameStore(slice)

        if fs.FrameNum != self.vps.PreviousFrameNum + 1 and fs.FrameNum != (self.vps.PreviousFrameNum + 1) % self.vps.max_frame_num:
            # TODO the frame is not continuous
            pass
        else:
            if fs.IdrPicFlag:
                self.idr_memory_management(fs)
            else:
                if fs.used_for_reference and fs.adaptive_ref_pic_marking_mode_flag:
                    # TODO adaptive ref picture marking
                    pass
                else:
                    pass

        self.insert_pic_in_dpb(fs)

    def idr_memory_management(self, fs):
        self.FrameList.clear()
        self.refFrameList0ShortTerm.clear()
        self.refFrameList0LongTerm.clear()

        if fs.long_term_reference_flag:
            fs.is_long_term = 3
            fs.LongTermFrameIdx = 0
        else:
            fs.is_long_term = 0
            fs.LongTermFrameIdx = -1

    def insert_pic_in_dpb(self, fs):
        self.FrameList.append(fs)

        self.refFrameList0LongTerm.clear()
        self.refFrameList0ShortTerm.clear()

        for f in self.FrameList:
            if f.used_for_reference:
                if f.is_long_term:
                    self.refFrameList0LongTerm.append(f)
                else:
                    self.refFrameList0ShortTerm.append(f)



class FrameStore:

    def __init__(self, slice):

        self.is_used = 3 # 0=empty; 1=top; 2=bottom; 3=both fields (or frame)
        self.is_reference = 1 # 0=not used for ref; 1=top used; 2=bottom used; 3=both fields (or frame) used
        self.used_for_reference = 1 if slice.nal_ref_idc != 0 else 0
        self.is_long_term = 0 # 0=not used for ref; 1=top used; 2=bottom used; 3=both fields (or frame) used

        self.FrameNum = slice.frame_num
        self.FrameNumWrap = 0
        self.PicNum = 0
        self.LongTermFrameIdx = -1
        self.LongTermPicNum = -1
        self.poc = slice.ThisPoc

        self.slice = slice

        self.IdrPicFlag = slice.IdrPicFlag
        self.adaptive_ref_pic_marking_mode_flag = 0 if slice.IdrPicFlag else slice.adaptive_ref_pic_marking_mode_flag
        self.long_term_reference_flag = slice.long_term_reference_flag if slice.IdrPicFlag else 0

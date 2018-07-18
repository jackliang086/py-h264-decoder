

class SEI:

    def __init__(self, bits, params):
        self.bits = bits
        for k in params:
            self.__dict__[k] = params[k]
        self.parse()

    def rbsp_trailing_bits(self):
        self.rbsp_stop_one_bit = self.bits.f(1)
        assert self.rbsp_stop_one_bit == 1
        while not self.bits.byte_aligned():
            assert self.bits.f(1) == 0

    def parse(self):
        self.sei_rbsp()

    def sei_rbsp(self):
        while True:
            self.sei_message()
            if not self.bits.more_rbsp_data():
                break
        self.rbsp_trailing_bits()

    def sei_message(self):
        payloadType = 0
        while self.bits.next_bits(8) == 0xff:
            ff_byte = self.bits.f(8)
            payloadType += ff_byte
        last_payload_type_byte = self.bits.u(8)
        payloadType += last_payload_type_byte
        payloadSize = 0
        while self.bits.next_bits(8) == 0xff:
            ff_byte = self.bits.f(8)
            payloadSize += ff_byte
        last_payload_size_byte = self.bits.u(8)
        payloadSize += last_payload_size_byte
        self.sei_payload(payloadType, payloadSize)

    def sei_payload(self, payloadType, payloadSize):
        # just read payloadSize content
        content = []
        for i in range(0, payloadSize):
            content.append(self.bits.u(8))




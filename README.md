# H.264 Baseline Decoder

This project is base on **halochou/py-h264-decoder** is able to decode YCbCr values from i-frame or **p-frame** in H.264 Baseline profile raw bitstream.

The project has the following features:

    1. explain h.264 baseline protocol element
    2. intra-frame prediction decode
    3. inter-frame prediction decode
    4. transform coefficient decode and quantization
    5. cavlc parse
    6. decode picture buffer
    7. deblocking filter

The program is written in Python 3.6.1, so you will need to install Python 3.6.1 or above together with dependency:

    pip install -r requirement.txt

The program can be executed as:

    python decoder.py

Then, the output folder will have the images that is the decoded frame. As shown below:

![Image](http://thyrsi.com/t6/358/1534492653x-1404755576.jpg)

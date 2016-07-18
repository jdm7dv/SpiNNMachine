

class FPGA(object):

    def __init__(self, fpga_id):
        self._associated_chips = list()
        self._fpga_id = fpga_id

    def add_chip(self, chip):
        self._associated_chips.append(chip)

    @property
    def chips(self):
        return self._associated_chips

    @property
    def fpga_id(self):
        return self._fpga_id

    def __repr__(self):
        output = ""
        output += "FPGA{} with chips {}".format(
            self._fpga_id, self._associated_chips)
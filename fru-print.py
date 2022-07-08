#!/usr/bin/env python3

__copyright__    = 'Copyright (C) 2022 ikwzm'
__version__      = '1.0.0'
__license__      = 'BSD-2-Clause'
__author__       = 'ikwzm'
__author_email__ = 'ichiro_k@ca2.so-net.ne.jp'
__url__          = 'https://github.com/ikwzm/fru-print'

from glob import glob
import itertools
import struct
import argparse
import yaml
import sys
import copy

class FRU:

    def validate_checksum(blob, offset, length, checksum = 0):
        data_sum = sum(
            struct.unpack('%dB' % (length), blob[offset:offset + length])
        )
        if 0xff & (data_sum + checksum) != 0:
            raise ValueError('The data does not match its checksum.')
    
    class CommonHeader:
        def __init__(self):
            self.version            = 0
            self.internal_offset    = 0
            self.chassis_offset     = 0
            self.board_offset       = 0
            self.product_offset     = 0
            self.multirecord_offset = 0
            self.data = {}

        def load_from_blob(self, blob):
            FRU.validate_checksum(blob, 0, 8)
            self.version            = ord(blob[0:1])
            self.internal_offset    = ord(blob[1:2]) * 8
            self.chassis_offset     = ord(blob[2:3]) * 8
            self.board_offset       = ord(blob[3:4]) * 8
            self.product_offset     = ord(blob[4:5]) * 8
            self.multirecord_offset = ord(blob[5:6]) * 8
            self.data = {'version': self.version, 'size': len(blob)}
            return self

    class InternalUse:
        def __init__(self):
            self.version = 0
            self.blob    = None
            self.offset  = 0
            self.length  = 0
            self.data    = {}
        
        def load_from_blob(self, blob, offset, length):
            self.offset  = offset
            self.version = ord(blob[self.offset + 0 : self.offset + 1])
            self.blob    = blob[self.offset + 1 : self.offset + length or len(blob)]
            self.length  = len(self.blob) + 1
            self.data    = {'data': self.blob}
            return self

    class Info:
        def __init__(self):
            self.items   = []
            self.version = 0
            self.offset  = 0
            self.size    = 0
            self.data    = {}

        def add_item(self, name, length = None, encoding = 0):
            self.items.append((name, length, encoding))
            return self

        def load_info_data(self, blob, offset):
            items = []
            for index, (name, length, encoding) in enumerate(self.items):
                last = (index == len(self.items)-1) and (length is not None)
                items.append((name, length, encoding, last))
            if last == False:
                extras = (('extra%d' % i , None, None, False) for i in itertools.count(1))
            else:
                extras = []
            for (name, length, encoding, last) in itertools.chain(items, extras):
                if length is None:
                    type_length = ord(blob[offset:offset + 1])
                    offset += 1
                    if type_length == 0xc1:
                        break;
                    length   = (type_length & 0x3f) >> 0
                    encoding = (type_length & 0xc0) >> 6
                ## print((name, length, encoding, last))
                if   encoding == 5:
                    data = blob[offset : offset+length]
                elif encoding == 4:
                    data = ord(blob[offset : offset+length])
                elif encoding == 3:
                    data = blob[offset : offset+length].decode('ascii').strip('\x00').strip()
                else:
                    data = blob[offset : offset+length].hex().strip()
                offset += length
                if name is not None:
                    self.data[name] = data
                if last == True:
                    break;
            return self.data

    class BoardInfo(Info):
        def __init__(self):
            super().__init__()
            self.add_item('language' , 1, 4)
            self.add_item('date'     , 3, 5)
            self.add_item('manufacturer'   )
            self.add_item('product'        )
            self.add_item('serial'         )
            self.add_item('part'           )
            self.add_item('fileid'         )
            self.add_item('revision'       )
            self.add_item('pcieinfo'       )
            self.add_item('uuid'           )
            
        def load_from_blob(self, blob, offset):
            self.offset  = offset
            self.version = ord(blob[self.offset + 0 : self.offset + 1])
            self.length  = ord(blob[self.offset + 1 : self.offset + 2]) * 8
            FRU.validate_checksum(blob, self.offset, self.length)
            self.load_info_data(blob, offset+2)
            if self.data.get('date'):
                date_blob = self.data['date']
                self.data['date'] = sum([
                    ord(date_blob[0:1]),
                    ord(date_blob[1:2]) << 8,
                    ord(date_blob[2:3]) << 16,
                 ])
            if self.data.get('pcieinfo'):
                pciinfo  = self.data['pcieinfo']
                self.data['pcieinfo'] = { \
                    'Vendor_ID':pciinfo[0:4], \
                    'Device_ID':pciinfo[4:8], \
                    'SubVendor_ID':pciinfo[8:12], \
                    'SubDevice_ID':pciinfo[12:16] \
                }
            return self
            
    class ChassisInfo(Info):
        def __init__(self):
            super().__init__()
            self.add_item('type'  , 1, 4)
            self.add_item('part'        )
            self.add_item('serial'      )

        def load_from_blob(self, blob, offset):
            self.offset  = offset
            self.version = ord(blob[self.offset + 0 : self.offset + 1])
            self.length  = ord(blob[self.offset + 1 : self.offset + 2]) * 8
            FRU.validate_checksum(blob, self.offset, self.length)
            self.load_info_data(blob, offset+2)
            return self
            
    class ProductInfo(Info):
        def __init__(self):
            super().__init__()
            self.add_item('language' , 1, 4)
            self.add_item('date'     , 3, 5)
            self.add_item('manufacturer'   )
            self.add_item('product'        )
            self.add_item('part'           )
            self.add_item('version'        )
            self.add_item('serial'         )
            self.add_item('asset'          )
            self.add_item('fileid'         )

        def load_from_blob(self, blob, offset):
            self.offset  = offset
            self.version = ord(blob[self.offset + 0 : self.offset + 1])
            self.length  = ord(blob[self.offset + 1 : self.offset + 2]) * 8
            FRU.validate_checksum(blob, self.offset, self.length)
            self.load_info_data(blob, offset+2)
            return self

    class RecordInfo(Info):
        def __init__(self, name, type_id):
            super().__init__()
            self.name          = name
            self.type_id       = type_id
            self.header_length = 5

        def load_type_id(self, blob, offset):
            return ord(blob[offset + 0 : offset + 1])       

        def load_version(self, blob, offset):
            return ord(blob[offset + 1 : offset + 2]) & 0x0F

        def load_end_of_list(self, blob, offset):
            flag = ord(blob[offset + 1 : offset + 2]) & 0x80
            return (flag != 0)
            
        def match(self, blob, offset):
            if offset+2 >= len(blob):
                return (None, True , 0)

            type_id     = self.load_type_id(blob, offset)
            version     = self.load_version(blob, offset)
            end_of_list = self.load_end_of_list(blob, offset)

            if self.type_id is not None and type_id != self.type_id:
                return (None, False, 0)

            if version > 2:
                return (None, False, 2)
            else:
                return (self, end_of_list, 0)
            
        def load_from_blob(self, blob, offset):
            self.offset        = offset
            self.version       = self.load_version(blob, offset)
            self.end_of_list   = self.load_end_of_list(blob, offset)
            self.record_offset = offset + self.header_length
            self.record_length = ord(blob[offset + 2 : offset + 3])
            self.record_csum   = ord(blob[offset + 3 : offset + 4])
            self.header_csum   = ord(blob[offset + 4 : offset + 5])
            self.length        = self.record_length + self.header_length
            FRU.validate_checksum(blob, offset, self.header_length)
            FRU.validate_checksum(blob, self.record_offset, self.record_length, self.record_csum)
            self.load_info_data(blob, self.record_offset)
            return self

    class DummyRecordInfo(RecordInfo):
        def __init__(self):
            super().__init__(None, None)
            self.add_item(None, 1, 0)

    class PowerSupplyRecordInfo(RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0x00)
            self.add_item('overall_capacity'          ,2, 0)
            self.add_item('peak_VA'                   ,2, 0)
            self.add_item('inrush_current'            ,1, 0)
            self.add_item('inrush_interval'           ,1, 0)
            self.add_item('input_voltage_range_1_low' ,2, 0)
            self.add_item('input_voltage_range_1_high',2, 0)
            self.add_item('input_voltage_range_2_low' ,2, 0)
            self.add_item('input_voltage_range_2_high',2, 0)
            self.add_item('input_frequency_range_low' ,1, 0)
            self.add_item('input_frequency_range_high',1, 0)
            self.add_item('input_dropout_tolerance'   ,1, 0)
            self.add_item('binary_flag'               ,1, 0)
            self.add_item('peak_wattage'              ,2, 0)
            self.add_item('combined_wattage'          ,3, 0)
            self.add_item('predictive_fail_tachometer',1, 0)

    class DCOutputRecordInfo(RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0x01)
            self.add_item('output_number'       ,1, 0)
            self.add_item('nominal_voltage'     ,2, 0)
            self.add_item('max_negative_voltage',2, 0)
            self.add_item('max_positive_voltage',2, 0)
            self.add_item('ripple/noise pk-pk'  ,2, 0)
            self.add_item('min_mA'              ,2, 0)
            self.add_item('max_mA'              ,2, 0)

    class DCLoadRecordInfo(RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0x02)
            self.add_item('output_number'       ,1, 0)
            self.add_item('nominal_voltage'     ,2, 0)
            self.add_item('min_V'               ,2, 0)
            self.add_item('max_V'               ,2, 0)
            self.add_item('ripple/noise pk-pk'  ,2, 0)
            self.add_item('min_mA'              ,2, 0)
            self.add_item('max_mA'              ,2, 0)
            
    class MultiRecord:
        def __init__(self):
            self.data                 = {}
            self.record_info_list     = []
            self.record_template_list = [FRU.DummyRecordInfo()]
            self.add_record_template(FRU.PowerSupplyRecordInfo('PowerSupply_Record'))
            self.add_record_template(FRU.DCOutputRecordInfo('DC_Output_Record'))
            self.add_record_template(FRU.DCLoadRecordInfo('DC_Load_Record'))

        def add_record_template(self, record_info):
            self.record_template_list.insert(-1,record_info)
            return self

        def load_from_blob(self, blob, offset):
            end_of_list = False
            while (end_of_list == False):
                for record_template in self.record_template_list:
                    (result, end_of_list, length) = record_template.match(blob, offset)
                    ## print(record_template.name, result, offset, length, end_of_list)
                    if result is None:
                        offset += length
                    else:
                        record_info = copy.deepcopy(result).load_from_blob(blob, offset)
                        name        = record_info.name
                        data        = record_info.data
                        end_of_list = record_info.end_of_list
                        length      = record_info.length
                        offset += length
                        self.record_info_list.append(record_info)
                        if name:
                            self.data[name] = data
                        break;
            return self
    
    def __init__(self):
        self.common_header    = FRU.CommonHeader()
        self.internal_use     = FRU.InternalUse()
        self.chassis_info     = FRU.ChassisInfo()
        self.board_info       = FRU.BoardInfo()
        self.product_info     = FRU.ProductInfo()
        self.multirecord      = FRU.MultiRecord()
        self.data             = {}

    def add_record_template(self, record):
        self.multirecord.add_record_template(record)
        return self

    def load_from_file(self, path=None):
        if path:
            with open(path, 'rb') as f:
                self.load_from_blob(f.read())
        return self

    def load_from_blob(self, blob=None):
        self.common_header.load_from_blob(blob)
        self.data = {'common': self.common_header.data}

        if self.common_header.internal_offset:
            next_offset = self.common_header.chassis_offset or \
                          self.common_header.board_offset   or \
                          self.common_header.product_offset
            size = next_offset - 1
            offset = self.common_header.internal_offset
            self.data['internal'] = self.internal_use.load_from_blob(blob, 1, offset, size)

        if self.common_header.chassis_offset:
            self.chassis_info.load_from_blob(blob, self.common_header.chassis_offset)
            self.data['chassis' ] = self.chassis_info.data

        if self.common_header.board_offset:
            self.board_info.load_from_blob(blob, self.common_header.board_offset)
            self.data['board'   ] = self.board_info.data

        if self.common_header.product_offset:
            self.product_info.load_from_blob(blob, self.common_header.product_offset)
            self.data['prodeuct'] = self.product_info.data

        if self.common_header.multirecord_offset:
            self.multirecord.load_from_blob(blob, self.common_header.multirecord_offset)
            self.data['multirecord'] = self.multirecord.data

        return self
        

class XilinxFRU(FRU):

    class ThermalRecordInfo(FRU.RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0xd0)
            self.add_item('Xilinx_IANA_ID',3, 0)
            self.add_item('Version'       ,1, 0)

    class PowerRecordInfo(FRU.RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0xd1)
            self.add_item('Xilinx_IANA_ID',3, 0)
            self.add_item('Version'       ,1, 0)

    class MacAddressRecordInfo(FRU.RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0xd2)
            self.add_item('Xilinx_IANA_ID',3, 0)
            self.add_item('Version'       ,1, 0)
            self.add_item('MAC_ID_0'      ,6, 0)
            
    class MemConfRecordInfo(FRU.RecordInfo):
        def __init__(self, name):
            super().__init__(name, 0xd3)
            self.add_item('Xilinx_IANA_ID'           , 3, 0)
            self.add_item(None                       , 8, 0)
            self.add_item('Primary_boot_device'      ,12, 3)
            self.add_item(None                       , 1, 0)
            self.add_item(None                       , 8, 0)
            self.add_item('SOM_secondary_boot_device',12, 3)
            self.add_item(None                       , 1, 8)
            self.add_item(None                       , 8, 8)
            self.add_item('SOM_PS_DDR_memory'        ,12, 3)
            self.add_item(None                       , 1, 0)
            self.add_item(None                       , 8, 0)
            self.add_item('SOM_PL_DDR_memory'        ,12, 3)
            self.add_item(None                       , 1, 0)
            
    def __init__(self):
        super().__init__()
        self.add_record_template(XilinxFRU.ThermalRecordInfo('Thermal'))
        self.add_record_template(XilinxFRU.PowerRecordInfo('Power'))
        self.add_record_template(XilinxFRU.MacAddressRecordInfo('MAC_Addr'))
        self.add_record_template(XilinxFRU.MemConfRecordInfo('SoM_Memory_Config'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='print fru data of SOM/CC eeprom')
    parser.add_argument('-b','--board'  , action='store', choices=['som','cc'], type=str,
                        help='Enter som or cc')
    parser.add_argument('-f','--field'  , action='store', nargs="+", type=str,
                        help='enter fields to index using. '
                             '(if entering one arg, it\'s assumed the field is from board area)')
    parser.add_argument('-s','--sompath', type=str, nargs="?", default='/sys/bus/i2c/devices/*50/eeprom',
                        help='enter path to SOM EEPROM')
    parser.add_argument('-c','--ccpath' , type=str, nargs="?", default='/sys/bus/i2c/devices/*51/eeprom',
                        help='enter path to CC EEPROM')
    args = parser.parse_args()

    if args.board == 'som':
        try:
            som = glob(args.sompath)[0]
        except:
            sys.exit('\n' 'sompath is incorrect:' + args.sompath)
    elif args.board == 'cc':
        try:
            cc  = glob(args.ccpath )[0]
        except:
            sys.exit('\n' 'ccpath is incorrect: ' + args.ccpath)
    else:
        try:
            som = glob(args.sompath)[0]
            cc  = glob(args.ccpath )[0]
        except:
            sys.exit('\n' 'One of the following paths is wrong:' +
                     '\n' 'som path: ' + args.sompath + 
                     '\n' 'cc path:  ' + args.ccpath)


    if args.field and args.board is None:
        parser.error('\n' 'If entering a field, need board input as well')

    elif args.board and args.field is None:
        fru = XilinxFRU().load_from_file(eval(args.board));
        print(yaml.dump(fru.data, default_flow_style=False, allow_unicode=True))

    elif args.board and args.field:
        try:
            fru = XilinxFRU().load_from_file(eval(args.board))
            if len(args.field) == 1:
                print(fru.data['board'][args.field[0]])
            else:
                for field in args.field:
                    data = fru.data['board'][field]
                    print(data)
        except KeyError:
            print("ERROR: "+str(args.field)+" is not a valid input for field.\n"
                  "multiple key values can be provided to the field arg, "
                  "ex. -f multirecord DC_Load_Record max_V\n"
                  "If just one value is given, it is assumed the field is under the board area.\n")
    else:
        som_fru = XilinxFRU().load_from_file(som)
        cc_fru  = XilinxFRU().load_from_file(cc )
        both    = {'som': som_fru.data, 'cc': cc_fru.data}
        print(yaml.dump(both,default_flow_style=False, allow_unicode=True))


#!/usr/bin/env python3

"""
# Utility for controlling RGB header on MSI boards
# The RGB header is controlled by the NCT6795D Super I/O chip.
#
# The Advanced "mode" is enabled by writing 87 87 to PORT 1.
# It is later disabled by writing AA
# to that same port. `07 12` then selects the bank 12h.
# This bank then looks like this:
#
# 00 |  ...
# 10 |  ...
# .  |
# .  |
# .  |
# E0 | EE XX XX XX  XP XX XX XX  XX XX XX XX  XX XX XX XX
# F0 | RR RR RR RR  GG GG GG GG  BB BB BB BB  XX XX TT TT
#     ---------------------------------------------------
#      00 01 02 03  04 05 06 07  08 09 0A 0B  0C 0D 0E 0F
#
# Here:
#
# Purpose of following bits in `EE` is known:
#
# `0b10000000` - red channel can handle 16 levels
# `0b01000000` - green channel can handle 16 levels
# `0b00100000` - blue channel can handle 16 levels
#
# If the corresponding bit is `0`, the channel always receives the maximum "brightness",
# regardless of setting.
#
#
# `R` - intensity of the red colour
# `G` - intensity of the green colour
# `B` - intensity of the blue colour
#
# There’s 8 distinct frames that can be specified,
# each defined by a 4 bit value for each color.
# When enumerating the frames from 0 to 7, then the sequence to be written into the four
# RR, GG, or BB bytes is: 10 32 54 76
#
# The frames change every given interval specified in the `TTTT` bytes. TTTT has the bit
# format like this: `tttttttt fffbgrdt`
#
# Here `t` bits are a duration between changes from one colour to another
# (takes the next column
# of RR GG BB). Bits 0-7 are stored in register 'FE',
# bit 8 in the least significant bit of 'FF'.;
#
# `d` bit specifies whether the RGB header is turned on
# (distinct from the motherboard lights).;
#
# `bgr` invert the intensity (`F` is 0%, `0` is 100%) for blue, green and red channels
# respectively.
#
# `fff` if set to 1 then the 8 frames of the RR, GG,
# and BB bytes behave as described above.  If
# set to 0 then a fade-in effect happens for blue, green and red channels respectively,
# but only
# when all 8 frames are set to 'f' value and only on the NCT6795D-M chip
# found e.g. on the B350 Tomahawk board.
#
# `P` here is another bitmask of the form `pbbb`,
# where `p` specifies whether smooth pulsing
# behaviour is enabled.
# `bbb` specifies duration between blinks.
# If `bbb` is `001`,
# all lightning is turned off, including the one on the motherboard itself.
# `000` is always on.
"""

from os import get_terminal_size
from argparse import ArgumentParser
from re import subn,sub
from sys import exit
from time import sleep
from pprint import pprint

class unk(list):
    __doc__="unknown purpose bits"
    def __init__(self,*z,**zz):
        if len(z)==1 and hasattr( z[0],'__int__'):
            super().__init__()
            ii=z[0]
            for i in range(ii.bit_length()-1,-1,-1):
                self.append(ii >> i)
        elif hasattr( z ,'__iter__'):
            super().__init__(z)
        elif type(z[0]) is bytes:
            super().__init__(z[0])

    def __len__(self):
        return self._len_()

    def __or__(self,val):
        i=self.__int__()
        return i|val

    def __ror__(self,val):
        i=self.__int__()
        return val | i 

    def _int_list_(self):
        b=[]
        for e in self:
            if type(e) is bytes:
                for ee in e:
                    b.append(ee)
            else:
                b.append(e)
        return b

    def __lshift__(self,val):
        i=self.__int__()
        return i << val

    def __int__(self):
        b=self._int_list_()
        bb=0
        for i in range(len(b)):
            e=b[i]
            bb|=e<<i
        return bb

class Bitseq(unk):
    __doc__="bit seq"
    def __init__(self,*z,**zz):
        descr=[]
        not_descr=[]
        for v in z:
            if type(v) is str:
                descr.append(v)
            else:
                not_descr.append(v)
        self.description='\n'.join(descr)
        super().__init__(*not_descr,**zz)

class Bit(Bitseq):
    def __init__(self,*z,**zz):
        super().__init__(1,*z,**zz)

def parse_args():
    a=ArgumentParser()
    #a.add_argument("--is-present",help="unknown what this is")
    a.add_argument  ( "--testing", action="store_true",default=True,
                      help="uses /tmp/msirgbpy.portfile to read/write to instead of the actual device"
                    )
    
    a.add_argument  ( "--disable", action="store_true",default=False,
                      help="disable the RGB subsystem altogether"
                    )
    a.add_argument  ( "--eat-the-cat-and-burn-the-house", action="store_true",default=False,
                      help=
                            "This software is untested und bugy as hell!\n"
                            "I converted the program to python and i have not such\n"
                            "a rgb controller.\n"
                            "It's sure that there are many bad bugs\n"
                            "Serious system damaging bugs should be expected\n"
                            "You need to check the program by reading the code\n"
                            "To verify that you did all precautions and that you\n"
                            "are responsible for the consequences, you need to\n"
                            "specify this argument run the program\n"
                            "Without this the testing mode is the only mode the program\n"
                            "does something.\n"
                    )
    a.add_argument  ( "-D","--debug", action="store",type=int,default=0,
                      help="if debug > 0 , enables debugging\n"
                           "some numbers overwrite /tmp/debuglog,\n"
                           "and opens append mode for debugging with dp(msg)"
                    )
    a.add_argument  ( "-v","--verbose", action="store_true",default=False,
                      help=""
                    )
    a.add_argument  ( "-q","--quiet", action="store_true",default=False,
                      help=""
                    )
    a.add_argument("--pulse",action='store_true',default=False,help="smooth pulsing")
    a.add_argument  (
                        "--ignorecheck",action='store_true',default=False,
                        help="ignore the result of sI/O identification check"
                    )
    a.add_argument("--blink",action='store_true',default=False,help="enables blink mode")
    a.add_argument  (
                        "-r","--red",type=str,default="00000000",
                        help="values of red colour (32 bit hex number, up to FFFFFFFF)"
                    )
    a.add_argument  (
                        "-g","--green",type=str,default="00000000",
                        help="values of green colour (32 bit hex number, up to FFFFFFFF)"
                    )
    a.add_argument  (
                        "-b","--blue",type=str,default="00000000",
                        help="values of green colour (32 bit hex number, up to FFFFFFFF)")
    a.add_argument  (
                        "--step-duration",type=int,default=128,
                        help="duration between distinct steps of colours\n"
                             "(0 - fastest, 511 - slowest"
                    )
    a.add_argument  (
                        "--base_port",type=str,default="4e",
                        help="Base-port to use. Values known to be in use are 4e and 2e"
                    )
    a.add_argument  (   "-i","--invhalf",type=str,default="",
                        help="syntax regex = \"^[rgb]*$\"\n"
                             "invert specified channels"
                    )
    a.add_argument  (   "-p","--prog",type=str,default=None,
                        help="Select a internal program by number.\n"
                             "To show avaiable one, see the --show option."
                    )
    a.add_argument  ( "-s","--show", action="store_true",default=False,
                      help="Show the avaiable inernal progs"
                    )
    a.add_argument  (
                        "-f","--fade-in",type=str,default="",
                        help="syntax regex = \"^[rgb]*$\"\n"
                             "Enable fade-in effect for specified channel(s)\n"
                             "(only works on some boards)"
                    )
    
    global args
    args=a.parse_args()

def dp(msg,postfix):
    if not args.debug:
        return
    with open('/tmp/debuglog_'+str(postfix),'at') as dlf:
        dlf.write(msg)

class Thing():
    """
    represents the thing
    """

    for c  in ('R','Red'),('G','Green'),('B','Blue'):
        for n in range(4,8):
            for p in ("a","c","e","g"):
                exec(c[0]+p+str(n)+"=Bitseq(\"Bit-"+str(n)+", "+c[1]+"-color ,timeslot-"+p+"\")")
        for n in range(4):
            for p in ("b","d","f","h"):
                exec(c[0]+p+str(n)+"=Bitseq(\"Bit-"+str(n)+", "+c[1]+"-color ,timeslot-"+p+"\")")

    r_16_cap = Bit( 1, "Makes Red   16-bit capable." )
    g_16_cap = Bit( 1, "Makes Green 16-bit capable." )
    b_16_cap = Bit( 1, "Makes Blue  16-bit capable." )

    addresses=  {
                    "0xe0" : r_16_cap<<7 | g_16_cap<<6 | b_16_cap<<5 |        unk(5)            ,
                    "0xe1" : unk(8)                                                             ,
                    "0xe2" : unk(8)                                                             ,
                    "0xe3" : unk(8)                                                             ,
                    "0xe4" :     unk(4)    |   smooth_p<<3 | blink_2<<2 | blink_1<<1 | blink_0  ,
                    "0xe5" :                          unk(8)                                    ,
                    "0xe6" :                          unk(8)                                    ,
                    "0xe7" :                          unk(8)                                    ,
                    "0xe8" :                          unk(8)                                    ,
                    "0xe9" :                          unk(8)                                    ,
                    "0xea" :                          unk(8)                                    ,
                    "0xeb" :                          unk(8)                                    ,
                    "0xec" :                          unk(8)                                    ,
                    "0xed" :                          unk(8)                                    ,
                    "0xee" :                          unk(8)                                    ,
                    "0xef" :                          unk(8)                                    ,
                    "0xf0" : Ra7<<7 | Ra6<<6 | Ra5<<5 | Ra4<<4 | Rb3<<3 | Rb2<<2 | Rb1<<1 | Rb0 ,
                    "0xf1" : Rc7<<7 | Rc6<<6 | Rc5<<5 | Rc4<<4 | Rd3<<3 | Rd2<<2 | Rd1<<1 | Rd0 ,
                    "0xf2" : Re7<<7 | Re6<<6 | Re5<<5 | Re4<<4 | Rf3<<3 | Rf2<<2 | Rf1<<1 | Rf0 ,
                    "0xf3" : Rg7<<7 | Rg6<<6 | Rg5<<5 | Rg4<<4 | Rh3<<3 | Rh2<<2 | Rh1<<1 | Rh0 ,
                    "0xf4" : Ga7<<7 | Ga6<<6 | Ga5<<5 | Ga4<<4 | Gb3<<3 | Gb2<<2 | Gb1<<1 | Gb0 ,
                    "0xf5" : Gc7<<7 | Gc6<<6 | Gc5<<5 | Gc4<<4 | Gd3<<3 | Gd2<<2 | Gd1<<1 | Gd0 ,
                    "0xf6" : Ge7<<7 | Ge6<<6 | Ge5<<5 | Ge4<<4 | Gf3<<3 | Gf2<<2 | Gf1<<1 | Gf0 ,
                    "0xf7" : Gg7<<7 | Gg6<<6 | Gg5<<5 | Gg4<<4 | Gh3<<3 | Gh2<<2 | Gh1<<1 | Gh0 ,
                    "0xf8" : Ba7<<7 | Ba6<<6 | Ba5<<5 | Ba4<<4 | Bb3<<3 | Bb2<<2 | Bb1<<1 | Bb0 ,
                    "0xf9" : Bc7<<7 | Bc6<<6 | Bc5<<5 | Bc4<<4 | Bd3<<3 | Bd2<<2 | Bd1<<1 | Bd0 ,
                    "0xfa" : Be7<<7 | Be6<<6 | Be5<<5 | Be4<<4 | Bf3<<3 | Bf2<<2 | Bf1<<1 | Bf0 ,
                    "0xfb" : Bg7<<7 | Bg6<<6 | Bg5<<5 | Bg4<<4 | Bh3<<3 | Bh2<<2 | Bh1<<1 | Bh0 ,
                    "0xfc" :                          unk(8)                                    ,
                    "0xfd" :                          unk(8)                                    ,
                    "0xfe" : ti7<<7 | ti6<<6 | ti5<<5 | ti4<<4 | ti3<<3 | ti2<<2 | ti1<<1 | ti0 ,
                    "0xff" : fa7<<7|fa6<<6|fa5<<5 | inv_b<<4|inv_g<<3|inv_r<<2 | rgb_en1<<1|ti8 ,
                }

    # constants
    RGB_BANK=0x12

    banks = [
                (RGB_BANK,  0xd0,   0x1000),
                (0x09,      0x20,   0x40),
                (0x0b,      0x60,   0x70),
            ]

    only_rgb_header_not_on_board_enable_bitmask = 0b10

    #             NCT6795, NCT6797
    VALID_MASKS=[ 0xD350,  0xD450 ]
    REG_DEVID_MSB = 0x20
    REG_DEVID_LSB = 0x21
    REDCELL       = 0xf0
    GREENCELL     = 0xf4
    BLUECELL      = 0xf8
    
    # settings
    check_rgb_enabled_all_time=True
    default_portfilepath="/dev/port"
    testing_portfilepath="/tmp/msirgbpy.portfile"

    class Printer():
        def __init__(self):
            print()
            self.hpos=0

        def print(self,*z,end='',indent=0,**zz):
            """
            The print function.
            Always the most important function.
            Therefor it's advisable to make it the most complex one.
            Obviously the goal is to make it as simple as
            possible without compromising
            the essential functionality.
            """
            txt = str(*z)+end
            #dp("<pos="+str(self.hpos)+">txt="+repr(txt),1)
            newline_pos_r=-1
            for i in range(len(txt)-1,-1,-1):
                if txt[i] == "\n" :
                    newline_pos_r=i
                    break
        
            newline_pos_l=-1
            for i in range(len(txt)):
                if txt[i] == "\n" :
                    newline_pos_l=i
                    break
        
            w = get_terminal_size().columns
            l=len(sub('\\n',"",txt))
        
            if newline_pos_r != -1 or newline_pos_l != -1:
                # newline somewhere, need to check
        
                if newline_pos_l + self.hpos > w:
                    #dp("<#d1#>",0)
                    # first newline would break to late
                    # so make fresh line
                    txt="\n"+" "*indent+txt
                    print(txt,end="")
                    self.hpos=indent
                else:
                    #dp("<d2>",0)
                    # need to attend, that
                    # pos is not self.hpos+len(txt) after print
                    print(txt,end="")
                    self.hpos = (l-newline_pos_r)
                    #dp("<pos="+str(self.hpos)+">",0)
                    #dp("<npr="+str(newline_pos_r)+">",0)
                    #dp("<l="+str(l)+">",0)
            else:
                # no newlines
                # so pos is self.hpos+len(txt) after print
                hpos_future=self.hpos+l
                if hpos_future > w:
                    print("\n"+" "*indent,end="")
                    self.hpos=indent
                print(txt,end="",**zz)
                self.hpos+=l

    class Device():
        def __init__(self,base_port,portfilepath,banks,printer,quiet=False,verbose=False):
            self.banks=banks
            self.verbose=verbose
            self.quiet=quiet
            self.base_port=base_port
            self.portfilepath=portfilepath
            self.printer=printer
            self._open()
            self._init_stage_0()
            self._init_stage_1()

        def _open(self):
            try:
                self.filehandle=open(self.portfilepath,"wb+")
            except:
                raise Exception("could not open \""+self.portfilepath+"\"; try sudo?")
            """
            #pub fn open_device() -> ::Result<fs::File> {
            #    fs::OpenOptions::new().read(true).write(true).open("/dev/port")
            #        .chain_err(|| { "could not open /dev/port; try sudo?" })
            """
    
        def _init_stage_0(self):
            try:
                self._outb( self.base_port, 0x87 )
                self._outb( self.base_port, 0x87 )
            except:
                raise Exception("could not enable advanced mode")
            """
            #fn run_wrap<'a>(matches: ArgMatches<'a>) -> Result<()> {
            #    let base_port = u16::from_str_radix(matches.value_of("BASEPORT")
            #                                               .expect("bug: BASEPORT argument"), 16)?;
            #
            #    let mut f = open_device()?;
            #    // Enable the advanced mode.
            #    self._outb(&mut f, base_port, 0x87).chain_err(|| "could not enable advanced mode")?;
            #    self._outb(&mut f, base_port, 0x87).chain_err(|| "could not enable advanced mode")?;
            #
            #
            #    let r = run(&mut f, base_port, matches);
            """
    
        def _init_stage_1(self):
            """
            These are something the built-in app does during initialization…
            Purpose unclear
            """
            init_stage1_verbose=False if self.quiet else self.verbose

            if init_stage1_verbose:
                self.printer.print(".init adv mode.")
            self._outb(    self.base_port,     b'\x07')
            if init_stage1_verbose:
                self.printer.print(".")
            self._outb(    self.base_port + 1, b'\x0B')
            if init_stage1_verbose:
                self.printer.print(".")
            self._outb(    self.base_port,     b'\x60')
            a = self._inb( self.base_port + 1)
            self._outb(    self.base_port,     b'\x61')
            b = self._inb( self.base_port + 1)
            if init_stage1_verbose:
                self.printer.print(".done.")
            """
            #    // These are something the built-in app does during initialization…
            #    // Purpose unclear
            #    // self._outb(&mut f, base_port, 0x07)?;
            #    // self._outb(&mut f, base_port + 1, 0x0B)?;
            #    // self._outb(&mut f, base_port, 0x60)?;
            #    // let a = self._inb(&mut f, base_port + 1)?;
            #    // self._outb(&mut f, base_port, 0x61)?;
            #    // let b = self._inb(&mut f, base_port + 1)?;
            #    // println!("{:x} {:x}", a, b);
            #    if matches.is_present("VERBOSE")  {
            #        print_all(&mut f, base_port)?;
            #    }
            """

        def _inb(self,port):
            if self.verbose:
                offset = port - self.base_port
                self.printer.print("r({:+d},".format(offset))
            self.filehandle.seek(port)
            data = self.filehandle.read(1)
            if self.verbose:
                self.printer.print("{:02x}) ".format( int.from_bytes( data,'little' )))
            return data
            """
            #pub fn _inb(f: &mut fs::File, port: u16) -> ::Result<u8> {
            #    let mut d = [0u8];
            #    f.seek(io::SeekFrom::Start(port.into()))?;
            #    f.read(&mut d)?;
            #    Ok(d[0])
            """

        def _outbo(self,offset,data):
            self._outb(self.base_port+offset,data)

        def _inbo(self,offset):
            return self._inb(self.base_port+offset)

        def _outb(self,port,data):
            if self.verbose:
                offset = port - self.base_port
                self.printer.print("w({:+d},".format(offset))
            oldv=self.verbose
            self.verbose=False
            a = self._inb( self.base_port + 1)
            self.verbose=oldv
            self.filehandle.seek(port)
            #if args.debug==2:
                #dp("base_port="+str(base_port)+"\n")
                #dp("port="+str(port)+"\n")
            t=type(data)
            if not t is bytes:
                if not t is int:
                    if self.verbose:
                        self.printer.print("..failed!")
                    raise Exception("ERROR data need type bytes or int")
                data=data.to_bytes(1,"little")
            if self.verbose:
                self.printer.print("{:02x}) ".format( data[0]))
            if not len(data)==1:
                if self.verbose:
                    self.printer.print("failed!")
                raise Exception("ERROR data need to be 1 byte long")
            l=self.filehandle.write(data)
            if l != 1:
                if self.verbose:
                    self.printer.print("failed!")
                raise Exception("write probably failed")
            """
            #pub fn _outb(f: &mut fs::File, port: u16, data: u8) -> ::Result<()> {
            #    f.seek(io::SeekFrom::Start(port.into()))?;
            #    f.write(&[data])?;
            """

        def print_all(self):
            oldv=self.verbose
            self.verbose=False
            for bank,s,e in self.banks:
                bank_msg="Bank[{:02x}]({:02x}...{:02x})=".format(bank, s, e)
                indent=len(bank_msg)
                self.printer.print("\n"+bank_msg,end="",indent=indent)
                #dp(bank_msg,2)
                self._outbo( 0 , 0x07 )
                self._outbo( 1 , bank )
                for x in range(101,116):
                    self._outbo( 0 , x )
                    d = self._inbo( 1 )
                    d=d[0]
                    if x & 0xf == 0xf :
                        ptxt="{:02x}".format(d)
                        etxt="\n"+" "*indent
                        self.printer.print(ptxt,end=etxt, indent=indent)
                        #dp(ptxt+etxt,2)
                        #dp("<d51>",2)
                    else:
                        ptxt="{:02x} ".format(d )
                        self.printer.print(ptxt,end="", indent=indent)
                        #dp(ptxt,2)
                        #dp("<d52>",2)
            self.printer.print(end="\n")
            self.verbose=oldv
            """
            #fn print_all(f: &mut fs::File, base_port: u16) -> Result<()> {
            #    for &(bank, s, e) in &[(RGB_BANK, 0xd0, 0x100u16), (0x09, 0x20, 0x40), (0x0b, 0x60, 0x70)] {
            #        println!("Bank {:02x} ({:02x}...{:02x}):", bank, s, e);
            #        _outb(f, base_port, 0x07)?;
            #        _outb(f, base_port + 1, bank)?;
            #
            #        for x in s..e {
            #            let x = x as u8;
            #            _outb(f, base_port, x)?;
            #            let d = _inb(f, base_port + 1)?;
            #            if x & 0xf == 0xf {
            #                println!("{:02x}", d);
            #            } else {
            #                print!("{:02x} ", d);
            #            }
            #        }
            #    }
            #    Ok(())
            #}
            """
            
        def _write_byte_to_cell( self, cell, data ):
            self._outb(self.base_port, cell )
            self._outb(self.base_port + 1, data )
            """
            #fn self._write_byte_to_cell(f: &mut fs::File, base_port: u16, cell: u8, data: u8) -> Result<()> {
            #    _outb(f, base_port, cell)?;
            #    _outb(f, base_port + 1, data)
            #}
            """
        
        def _deinit(self):
            """
            # Disable the advanced mode.
            """
            try:
                self._outb( self.base_port, 0xAA)
            except:
                raise Exception("could not disable advanced mode")
            """
            #    // Disable the advanced mode.
            #    self._outb(&mut f, base_port, 0xAA).chain_err(|| "could not disable advanced mode")?;
            #    r.chain_err(|| "could not set the colour")
            #}
            """
    
    def __init__(self,*z,args=None,**zz):
        self.args=args
        
        if self.args.testing:
            portfilepath=self.testing_portfilepath
        else:
            portfilepath=self.default_portfilepath

        self.printer=self.Printer()

        base_port=int(self.args.base_port,base=16)
        if not self.args.quiet:
            self.printer.print("base port = "+str(base_port),end="\n")


        self.dev=self.Device (
                                    base_port,
                                    portfilepath,
                                    self.banks,
                                    self.printer,
                                    quiet=self.args.quiet,
                                    verbose=args.verbose,
                                )

        self._data_is_up2date=False
        self._hardware_ckecked_and_ok=False
        self._pulsing_initialized=False
        self._checked_rgb_enabled=False

    def __del__(self):
        self.dev._deinit()

    def _write_color(self, cell_offset , data ):
        self.dev._write_byte_to_cell( cell_offset, (data >> 24))
        self.dev._write_byte_to_cell( cell_offset + 1 , (data >> 16))
        self.dev._write_byte_to_cell( cell_offset + 2 , (data >> 8))
        self.dev._write_byte_to_cell( cell_offset + 3 , data)
        """
        #fn self._write_color(f: &mut fs::File, base_port: u16, cell_offset: u8, data: u32) -> Result<()> {
        #    self._write_byte_to_cell(f, base_port, cell_offset, (data >> 24) as u8)?;
        #    self._write_byte_to_cell(f, base_port, cell_offset + 1, (data >> 16) as u8)?;
        #    self._write_byte_to_cell(f, base_port, cell_offset + 2, (data >> 8) as u8)?;
        #    self._write_byte_to_cell(f, base_port, cell_offset + 3, data as u8)
        #}
        """

    def _calc_data(self):
        if self._data_is_up2date:
            return
        self.data={}
        # prepare the cmdline arguments
        self.data.update({ 'red'  : (int(args.red,   base=16) & 0x00000000)})
        self.data.update({ 'green': (int(args.green, base=16) & 0x00000000)})
        self.data.update({ 'blue' : (int(args.blue,  base=16) & 0x00000000)})

        step_duration=(args.step_duration if (args.step_duration < 512) else 511) 
        self.data.update({ 'step_duration' : step_duration })
    
        self.data.update({ 'invert_red'   : False if not "r" in args.invhalf else True})
        self.data.update({ 'invert_green' : False if not "g" in args.invhalf else True})
        self.data.update({ 'invert_blue'  : False if not "b" in args.invhalf else True})
    
        self.data.update({ 'fade_in_red'   : False if not "r" in args.fade_in else True})
        self.data.update({ 'fade_in_green' : False if not "g" in args.fade_in else True})
        self.data.update({ 'fade_in_blue'  : False if not "b" in args.fade_in else True})
        self._calc_e4_val()

        ff_fade_in_val = ~0b0
        if self.data['fade_in_blue']:
            ff_fade_in_val = ~0b10000000 & ff_fade_in_val
        if self.data['fade_in_green']:
            ff_fade_in_val = ~0b01000000 & ff_fade_in_val
        if self.data['fade_in_red']:
            ff_fade_in_val = ~0b00100000 & ff_fade_in_val
        ff_fade_in_val = 0b11100000 & ff_fade_in_val # no fading in at all.
        self.data.update({'ff_fade_in_val':ff_fade_in_val})

        ff_invert_val = 0b0
        if self.data['invert_blue']:
            ff_invert_val = 0b00010000 & ff_invert_val
        if self.data['invert_green']:
            ff_invert_val = 0b00001000 & ff_invert_val
        if self.data['invert_red']:
            ff_invert_val = 0b00000100 & ff_invert_val
        self.data.update({'ff_invert_val':ff_invert_val})

        self._calc_ff_val()

        self._data_is_up2date=True

        """
        #    let ff_fade_in_val = 0b11100000u8 & // no fading in at all.
        #        if fade_in.contains(&"b") { !0b10000000 } else { !0 } &
        #        if fade_in.contains(&"g") { !0b01000000 } else { !0 } &
        #        if fade_in.contains(&"r") { !0b00100000 } else { !0 };
        
        #    let ff_invert_val = 0u8 |
        #        if invs.contains(&"b") { 0b00010000 } else { 0 } |
        #        if invs.contains(&"g") { 0b00001000 } else { 0 } |
        #        if invs.contains(&"r") { 0b00000100 } else { 0 } ;
        """

    def _calc_e4_val(self):
        self.data.update({'e4_val':None})
        if self.args.disable:
            self.data['e4_val']=1
        elif self.args.pulse:
            self.data['e4_val']=0b1000
        elif not self.args.blink == 0:
            self.data['e4_val']=(self.args.blink + 1) & 0b111
        else:
            self.data['e4_val']=0

    def _calc_ff_val(self):
        extra_step_duration_bit = (self.data['step_duration'] >> 8).to_bytes(1,'little')[0] & 1

        ff_val = extra_step_duration_bit \
                | self.only_rgb_header_not_on_board_enable_bitmask \
                | self.data['ff_invert_val'] \
                | self.data['ff_fade_in_val']
        self.data.update({'ff_val':ff_val})

    def _check_hardware(self):
        """
        # Check if indeed a NCT6795D
        """
        if self._hardware_ckecked_and_ok:
            return
        if not self.args.ignorecheck and not self.args.testing:
            self.dev._outbo( 0 , self.REG_DEVID_MSB)
            msb = self.dev._inbo( 1)
            self.dev._outbo( 0 , self.REG_DEVID_LSB)
    
            indent = ( msb[0] << 8 ) | (0x00 + self.dev._inbo( 1 )[0])
    
            if self.args.verbose:
                self.printer.print("Chip identifier is: {:x}".format(ident))
            if not (indent & 0xFFF0) in self.VALID_MASKS:
                raise Exception (    
                                    "--ignorecheck flag, which would skip the check;"
                                    "is not specified (may be dangerous);"
                                    "also try --base-port"
                                )
                raise Exception (
                                    "The sI/O chip identifies as {:x}, which does not"
                                    "seem to be NCT6795D".format(ident)
                                )
        self._hardware_ckecked_and_ok=True

    def _init_pulsing(self):
        """
        # Without this pulsing does not work
        """
        if self._pulsing_initialized:
            return
        self.dev._outbo( 0 , 0x07)
        self.dev._outbo( 1 , 0x09)
        self.dev._outbo( 0 , 0x2c)
        c = (self.dev._inbo( 1 ))[0]
        if c & 0x10 != 0x10 :
            self.dev._outbo( 1, c | 0x10)
        self._pulsing_initialized=True

    def _select_bank_12(self):
        """
        # Select the 0x12th bank.
        """
        self.dev._outbo( 0 , 0x07)
        self.dev._outbo( 1 , self.RGB_BANK)
    
    def _check_rgb_enabled(self):
        """
        # Check if RGB control enabled?
        """
        if self._checked_rgb_enabled and not self.check_rgb_enabled_all_time:
            return
        self.dev._outbo( 0 , 0xe0)
        d = self.dev._inbo( 1)[0]
        if d & 0xe0 != 0xe0 :
            self.dev._outbo(  1, 0xe0 | (d & ~0xe0))
        self._checked_rgb_enabled=True

    def _prepare_data_write(self):
        self._calc_data()
        self._check_hardware()
        self._init_pulsing()
        self._select_bank_12()
        self._check_rgb_enabled()

    def write_data(self):
        self._prepare_data_write()

        self.dev._write_byte_to_cell(  0xe4, self.data['e4_val'])
        self.dev._write_byte_to_cell(  0xfe, self.data['step_duration'])
        self.dev._write_byte_to_cell(  0xff, self.data['ff_val'])
    
        self._write_color(  self.REDCELL,   self.data['red'])
        self._write_color(  self.GREENCELL, self.data['green'])
        self._write_color(  self.BLUECELL,  self.data['blue'])

def init():
    parse_args()
    if not args.testing and not args.eat_the_cat_and_burn_the_house:
        print   (   
                    "The program exits to protect the user."
                    "Use the --help option to get some information"
                )
        exit()

def main():
    """
    """
    init()

    if args.show:
        pprint(progs)
        exit()

    global thing
    thing=Thing(args=args)
    
    if args.verbose:
        thing.dev.print_all()
    
    if args.prog is None:
        thing.write_data()
    else:
        progs[args.prog](thing)

    thing.__del__()

def internal_prog_1(thing):
    while True:
        thing.args.invhalf="bg"
        thing.args.red="00000000"
        thing.args.green="00000000" 
        thing.args.green="00000000"
        thing.write_data()
        sleep(1)
        thing.args.invhalf="rb"
        thing.write_data()

progs={ "1" : internal_prog_1 }

if __name__=='__main__':
    main()
    
    
# vim: set syntax=python foldmethod=indent foldlevel=0 foldnestmax=4:

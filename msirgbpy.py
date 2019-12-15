#!/usr/bin/env python3

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


from os import get_terminal_size
from argparse import ArgumentParser
from re import sub
from sys import exit
from time import sleep
from pprint import pprint

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
                    "--stepduration",type=int,default=128,
                    help="duration between distinct steps of colours\n"
                         "(0 - fastest, 511 - slowest"
                )
a.add_argument  (
                    "--baseport",type=str,default="4e",
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

def parse_args():
    global args
    args=a.parse_args()


RGB_BANK=0x12
#             NCT6795, NCT6797
VALID_MASKS=[ 0xD350,  0xD450 ]
REG_DEVID_MSB = 0x20
REG_DEVID_LSB = 0x21
REDCELL       = 0xf0
GREENCELL     = 0xf4
BLUECELL      = 0xf8

default_portfilepath="/dev/port"
testing_portfilepath="/tmp/msirgbpy.portfile"

filehandle = None

# redefine print
o_print=print
def print(*z,end='',**zz):
    """
    The print function.
    Always the most important function.
    Therefor it's advisable to make it the most complex one.
    Obviously the goal is to make it as simple as
    possible without compromising
    the essential functionality.
    """
    global hpos
    txt = str(*z)+end
    newline_pos_r=-1
    for i in range(len(txt),-1,-1):
        if i == "\n" :
            newline_pos_r=i
            break

    newline_pos_l=-1
    for i in range(len(txt)):
        if i == "\n" :
            newline_pos_l=i
            break

    w = get_terminal_size().columns
    l=len(sub("\\n","",txt))

    if args.debug == 9:
        if newline_pos_r != -1 or newline_pos_l != -1:
            dp("find: "+str(newline_pos_l)+" "+str(l)+" "+str(newline_pos_r)+" hpos="+str(hpos)+"\n")

        # newline somewhere, need to check
        if newline_pos_l + hpos > w:
            # first newline would break to late
            # so first make fresh line
            o_print("\n"+txt)
            hpos=0
            if args.debug==9:
                dp('.d1.')
        else:
            # need to attend, that
            # pos is not hpos+len(txt) after print
            o_print(txt)
            pos = (l-newline_pos_r)
    else:
        # no newlines
        # so pos is hpos+len(txt) after print
        hpos_future=hpos+l
        if hpos_future > w:
            o_print()
            hpos=0
        o_print(txt,end="",**zz)
        hpos+=l

def inb(port,verbose='args'):
    if verbose=="args" and not args.quiet:
        verbose_=args.verbose
    elif verbose is True:
        verbose_=True
    elif verbose is False:
        verbose_=False
    verbose=verbose_
    global printverbose
    verbose=verbose if verbose is False else printverbose
    if verbose:
        global base_port
        offset = base_port - port
        print("r({:+d},".format(offset))
    global filehandle
    filehandle.seek(port)
    data = filehandle.read(1)
    if verbose:
        print("{:02x}) ".format( int.from_bytes(data,'little' )))
    return data
    #pub fn inb(f: &mut fs::File, port: u16) -> ::Result<u8> {
    #    let mut d = [0u8];
    #    f.seek(io::SeekFrom::Start(port.into()))?;
    #    f.read(&mut d)?;
    #    Ok(d[0])

def outb(port,data,verbose='args'):
    global printverbose
    if verbose=="args" and not args.quiet:
        verbose_=args.verbose
    elif verbose is True:
        verbose_=True
    elif verbose is False:
        verbose_=False
    verbose=verbose_
    verbose = False if verbose is False else printverbose
    if verbose:
        global base_port
        offset = base_port - port
        print("w({:+d},".format(offset))
    a = inb( base_port + 1,verbose=False)
    global filehandle
    filehandle.seek(port)
    if args.debug==2:
        print("#####."+str(port)+".####")
    t=type(data)
    if not t is bytes:
        if not t is int:
            if verbose:
                print("..failed!")
            raise Exception("ERROR data need type bytes or int")
        data=data.to_bytes(1,"little")
    if verbose:
        print("{:02x}) ".format( data[0]))
    if not len(data)==1:
        if verbose:
            print("failed!")
        raise Exception("ERROR data need to be 1 byte long")
    l=filehandle.write(data)
    if l != 1:
        if verbose:
            print("failed!")
        raise Exception("write probably failed")
    #pub fn outb(f: &mut fs::File, port: u16, data: u8) -> ::Result<()> {
    #    f.seek(io::SeekFrom::Start(port.into()))?;
    #    f.write(&[data])?;

def open_device():
    global filehandle
    try:
        filehandle=open(portfilepath,"wb+")
    except:
        raise Exception("could not open \""+portfilepath+"\"; try sudo?")
    #pub fn open_device() -> ::Result<fs::File> {
    #    fs::OpenOptions::new().read(true).write(true).open("/dev/port")
    #        .chain_err(|| { "could not open /dev/port; try sudo?" })



def write_byte_to_cell( base_port, cell, data ):
    global filehandle
    outb(base_port, cell)
    outb(base_port + 1, data)
#fn write_byte_to_cell(f: &mut fs::File, base_port: u16, cell: u8, data: u8) -> Result<()> {
#    outb(f, base_port, cell)?;
#    outb(f, base_port + 1, data)
#}

def write_colour( base_port, cell_offset , data ):
    write_byte_to_cell( base_port, cell_offset, (data >> 24))
    write_byte_to_cell( base_port, cell_offset + 1 , (data >> 16))
    write_byte_to_cell( base_port, cell_offset + 2 , (data >> 8))
    write_byte_to_cell( base_port, cell_offset + 3 , data)
#fn write_colour(f: &mut fs::File, base_port: u16, cell_offset: u8, data: u32) -> Result<()> {
#    write_byte_to_cell(f, base_port, cell_offset, (data >> 24) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 1, (data >> 16) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 2, (data >> 8) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 3, data as u8)
#}


def run( base_port ):

    # prepare the cmdline arguments
    red   = (int(args.red,   base=16) & 0x00000000)
    green = (int(args.green, base=16) & 0x00000000)
    blue  = (int(args.blue,  base=16) & 0x00000000)

    step_duration = args.stepduration

    invert_red   = False if not "r" in args.invhalf else True
    invert_green = False if not "g" in args.invhalf else True
    invert_blue  = False if not "b" in args.invhalf else True

    fade_in_red   = False if not "r" in args.fade_in else True
    fade_in_green = False if not "g" in args.fade_in else True
    fade_in_blue  = False if not "b" in args.fade_in else True

    # Check if indeed a NCT6795D
    if not args.ignorecheck and not args.testing:
        outb( base_port, REG_DEVID_MSB)
        msb = inb( base_port + 1)
        outb( base_port, REG_DEVID_LSB)

        indent = ( msb[0] << 8 ) | (0x00 + inb( base_port + 1 )[0])

        if args.verbose:
            print("Chip identifier is: {:x}".format(ident))
        if not (indent & 0xFFF0) in VALID_MASKS:
            raise Exception (    
                                "--ignorecheck flag, which would skip the check;"
                                "is not specified (may be dangerous);"
                                "also try --base-port"
                            )
            raise Exception (
                                "The sI/O chip identifies as {:x}, which does not"
                                "seem to be NCT6795D".format(ident)
                            )

    # Without this pulsing does not work
    outb( base_port, 0x07)
    outb( base_port + 1, 0x09)
    outb( base_port, 0x2c)
    c = (inb(base_port + 1))[0]
    if c & 0x10 != 0x10 :
        outb(base_port + 1, c | 0x10)

    # Select the 0x12th bank.
    outb(base_port, 0x07)
    outb(base_port + 1, RGB_BANK)

    # Check if RGB control enabled?
    outb(base_port, 0xe0)
    d = inb( base_port + 1)[0]

    if d & 0xe0 != 0xe0 :
        outb( base_port + 1, 0xe0 | (d & ~0xe0))
    if args.disable:
        e4_val=1
    elif args.pulse:
        e4_val=0b1000
    elif not args.blink == 0:
        e4_val=(args.blink + 1) & 0b111
    else:
        e4_val=0

    write_byte_to_cell( base_port, 0xe4, e4_val)
    write_byte_to_cell( base_port, 0xfe, (step_duration if (step_duration < 512) else 511))

    ff_fade_in_val = ~0b0
    if fade_in_blue:
        ff_fade_in_val = ~0b10000000 & ff_fade_in_val
    if fade_in_green:
        ff_fade_in_val = ~0b01000000 & ff_fade_in_val
    if fade_in_red:
        ff_fade_in_val = ~0b00100000 & ff_fade_in_val
    ff_fade_in_val = 0b11100000 & ff_fade_in_val # no fading in at all.
#    let ff_fade_in_val = 0b11100000u8 & // no fading in at all.
#        if fade_in.contains(&"b") { !0b10000000 } else { !0 } &
#        if fade_in.contains(&"g") { !0b01000000 } else { !0 } &
#        if fade_in.contains(&"r") { !0b00100000 } else { !0 };

    ff_invert_val = 0b0
    if invert_blue:
        ff_invert_val = 0b00010000 & ff_invert_val
    if invert_green:
        ff_invert_val = 0b00001000 & ff_invert_val
    if invert_red:
        ff_invert_val = 0b00000100 & ff_invert_val
#    let ff_invert_val = 0u8 |
#        if invs.contains(&"b") { 0b00010000 } else { 0 } |
#        if invs.contains(&"g") { 0b00001000 } else { 0 } |
#        if invs.contains(&"r") { 0b00000100 } else { 0 } ;




    ff_val = (step_duration >> 8).to_bytes(1,'little')[0] \
        & 1 | 0b10 | ff_invert_val | ff_fade_in_val
    # (step_duration >> 8) as u8 & 0b1 | // The extra bit for step duration
    #  0b10 | // if 0 disable lights on rgb header only, not on board

    write_byte_to_cell(base_port, 0xff, ff_val)

    write_colour( base_port, REDCELL, red)
    write_colour( base_port, GREENCELL, green)
    write_colour( base_port, BLUECELL, blue)

def print_all(filehandle,base_port):
    global hpos
    for bank,s,e in [
                        (RGB_BANK,  0xd0,   0x1000),
                        (0x09,      0x20,   0x40),
                        (0x0b,      0x60,   0x70),
                    ]:
        print(end="\n")
        bank_msg="Bank[{:02x}]({:02x}...{:02x})=".format(bank, s, e)
        indent=len(bank_msg)
        print(bank_msg,end="")
        outb(base_port, 0x07, verbose=False )
        outb(base_port + 1, bank,verbose=False)
        for x in range(101,116):
            outb( base_port, x,verbose=False)
            d = inb( base_port + 1,verbose=False)
            d=d[0]
            if x & 0xf == 0xf :
                ptxt="{:02x}".format(d)
                etxt="\n"+" "*indent
                if args.debug == 9:
                    dp('\nBREAK\nhpos:'+str(hpos)+'\n'+"ptxt="+repr(ptxt)+"\netxt="+repr(etxt)+"<<<\n\n")
                print(ptxt,end=etxt)
            else:
                ptxt="{:02x} ".format(d )
                if args.debug == 9:
                    dp('  hpos:'+str(hpos)+'  '+"ptxt="+repr(ptxt))
                print(ptxt,end="")

#fn print_all(f: &mut fs::File, base_port: u16) -> Result<()> {
#    for &(bank, s, e) in &[(RGB_BANK, 0xd0, 0x100u16), (0x09, 0x20, 0x40), (0x0b, 0x60, 0x70)] {
#        println!("Bank {:02x} ({:02x}...{:02x}):", bank, s, e);
#        outb(f, base_port, 0x07)?;
#        outb(f, base_port + 1, bank)?;
#
#        for x in s..e {
#            let x = x as u8;
#            outb(f, base_port, x)?;
#            let d = inb(f, base_port + 1)?;
#            if x & 0xf == 0xf {
#                println!("{:02x}", d);
#            } else {
#                print!("{:02x} ", d);
#            }
#        }
#    }
#    Ok(())
#}
#

def dp(msg):
    with open('/tmp/debuglog','at') as dlf:
        dlf.write(msg)

def run_wrap(progs={}):
    """
    Wrapper which enables and disables the advanced mode
    """
    global base_port
    base_port=int(args.baseport,base=16)
    global filehandle
    open_device()
    try:
        outb( base_port, 0x87 )
        outb( base_port, 0x87 )
    except:
        raise Exception("could not enable advanced mode")

    # These are something the built-in app does during initialization…
    # Purpose unclear
    advanced_mode_verbose=False if args.quiet else args.verbose
    if advanced_mode_verbose:
        print(".init adv mode.")
    outb(    base_port,     b'\x07')
    if advanced_mode_verbose:
        print(".")
    outb(    base_port + 1, b'\x0B')
    if advanced_mode_verbose:
        print(".")
    outb(    base_port,     b'\x60')
    a = inb( base_port + 1)
    outb(    base_port,     b'\x61')
    b = inb( base_port + 1)
    if advanced_mode_verbose:
        print(".done.")
    

    if args.verbose:
        print_all(filehandle, base_port)
    if not args.prog is None:
        r = progs[args.prog](base_port)
    else:
        r = run( base_port )
    # Disable the advanced mode.
    try:
        outb( base_port, 0xAA)
    except:
        raise Exception("could not disable advanced mode")

#fn run_wrap<'a>(matches: ArgMatches<'a>) -> Result<()> {
#    let base_port = u16::from_str_radix(matches.value_of("BASEPORT")
#                                               .expect("bug: BASEPORT argument"), 16)?;
#
#    let mut f = open_device()?;
#    // Enable the advanced mode.
#    outb(&mut f, base_port, 0x87).chain_err(|| "could not enable advanced mode")?;
#    outb(&mut f, base_port, 0x87).chain_err(|| "could not enable advanced mode")?;
#
#    // These are something the built-in app does during initialization…
#    // Purpose unclear
#    // outb(&mut f, base_port, 0x07)?;
#    // outb(&mut f, base_port + 1, 0x0B)?;
#    // outb(&mut f, base_port, 0x60)?;
#    // let a = inb(&mut f, base_port + 1)?;
#    // outb(&mut f, base_port, 0x61)?;
#    // let b = inb(&mut f, base_port + 1)?;
#    // println!("{:x} {:x}", a, b);
#    if matches.is_present("VERBOSE")  {
#        print_all(&mut f, base_port)?;
#    }
#
#    let r = run(&mut f, base_port, matches);
#    // Disable the advanced mode.
#    outb(&mut f, base_port, 0xAA).chain_err(|| "could not disable advanced mode")?;
#    r.chain_err(|| "could not set the colour")
#}
#
def init():
    o_print()
    global hpos
    hpos=0
    parse_args()
    if not args.testing and not args.eat_the_cat_and_burn_the_house:
        print   (   
                    "The program exits to protect the user."
                    "Use the --help option to get some information"
                )
        exit()
    global printverbose
    printverbose=args.verbose
    global portfilepath
    if args.testing:
        portfilepath=testing_portfilepath
    else:
        portfilepath=default_portfilepath

def internal_prog_1(*z,**zz):
    while True:
        run(*z,**zz)
        args.invhalf="bg"
        args.red="00000000"
        args.green="00000000" 
        args.green="00000000"
        sleep(10)
        args.invhalf="rb"
        run(*z,**zz)

progs={ "1" : internal_prog_1 }

if __name__=='__main__':
    init()
    if args.show:
        pprint(progs)
        exit()
    run_wrap(progs=progs)
    
    
# vim: set syntax=python :

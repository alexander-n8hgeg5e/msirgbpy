#!/usr/bin/env python3
#//! Utility for controlling RGB header on MSI boards
#//!
#//! The RGB header is controlled by the NCT6795D Super I/O chip.
#//!
#//! The Advanced "mode" is enabled by writing 87 87 to PORT 1. It is later disabled by writing AA
#//! to that same port. `07 12` then selects the bank 12h. This bank then looks like this:
#//!
#//! 00 |  ...
#//! 10 |  ...
#//! .  |
#//! .  |
#//! .  |
#//! E0 | EE XX XX XX  XP XX XX XX  XX XX XX XX  XX XX XX XX
#//! F0 | RR RR RR RR  GG GG GG GG  BB BB BB BB  XX XX TT TT
#//!     ---------------------------------------------------
#//!      00 01 02 03  04 05 06 07  08 09 0A 0B  0C 0D 0E 0F
#//!
#//! Here:
#//!
#//! Purpose of following bits in `EE` is known:
#//!
#//! `0b10000000` - red channel can handle 16 levels
#//! `0b01000000` - green channel can handle 16 levels
#//! `0b00100000` - blue channel can handle 16 levels
#//!
#//! If the corresponding bit is `0`, the channel always receives the maximum "brightness",
#//! regardless of setting.
#//!
#//!
#//! `R` - intensity of the red colour
#//! `G` - intensity of the green colour
#//! `B` - intensity of the blue colour
#//!
#//! There’s 8 distinct frames that can be specified, each defined by a 4 bit value for each color.
#//! When enumerating the frames from 0 to 7, then the sequence to be written into the four
#//! RR, GG, or BB bytes is: 10 32 54 76
#//!
#//! The frames change every given interval specified in the `TTTT` bytes. TTTT has the bit
#//! format like this: `tttttttt fffbgrdt`
#//!
#//! Here `t` bits are a duration between changes from one colour to another (takes the next column
#//! of RR GG BB). Bits 0-7 are stored in register 'FE', bit 8 in the least significant bit of 'FF'.;
#//!
#//! `d` bit specifies whether the RGB header is turned on (distinct from the motherboard lights).;
#//!
#//! `bgr` invert the intensity (`F` is 0%, `0` is 100%) for blue, green and red channels
#//! respectively.
#//!
#//! `fff` if set to 1 then the 8 frames of the RR, GG, and BB bytes behave as described above.  If
#//! set to 0 then a fade-in effect happens for blue, green and red channels respectively, but only
#//! when all 8 frames are set to 'f' value and only on the NCT6795D-M chip found e.g. on the B350
#//! Tomahawk board.
#//!
#//! `P` here is another bitmask of the form `pbbb`, where `p` specifies whether smooth pulsing
#//! behaviour is enabled. `bbb` specifies duration between blinks. If `bbb` is `001`,
#//! all lightning is turned off, including the one on the motherboard itself. `000` is always on.
from argparse import ArgumentParser
from .platform.linux import *
a=ArgumentParser()
#a.add_argument("--is-present",help="unknown what this is")
a.add_argument  ( "--disable", action="store_true",default=False,
                  help="disable the RGB subsystem altogether"
                )
a.add_argument("--pulse",action='store_true',default=False,help="smooth pulsing")
a.add_argument  (
                    "--ignorecheck",action='store_true',default=False
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
a.add_argument  (
                    "--fade_in",type=str,default="",
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
REG_DEVID_MSB= 0x20
REG_DEVID_LSB= 0x21
REDCELL=0xf0
GREENCELL=0xf4
BLUECELL=0xf8

file = None

def inb(port):
    global file
    file.seek(port)
    return file.read(1)
    #pub fn inb(f: &mut fs::File, port: u16) -> ::Result<u8> {
    #    let mut d = [0u8];
    #    f.seek(io::SeekFrom::Start(port.into()))?;
    #    f.read(&mut d)?;
    #    Ok(d[0])

def outb(port,data)
    global file
    file.seek(port)
    if not type(data) is bytes:
        raise Exception("data need txpe bytes")
    data=data[0]
    l=file.write(data)
    if l != 1:
        raise Exception("write prpbably failed")
    #pub fn outb(f: &mut fs::File, port: u16, data: u8) -> ::Result<()> {
    #    f.seek(io::SeekFrom::Start(port.into()))?;
    #    f.write(&[data])?;

def open_device():
    global file
    try:
        file=open("/dev/port")
    except:
        raise Exception("could not open /dev/port; try sudo?")
    #pub fn open_device() -> ::Result<fs::File> {
    #    fs::OpenOptions::new().read(true).write(true).open("/dev/port")
    #        .chain_err(|| { "could not open /dev/port; try sudo?" })



def write_byte_to_cell(file, base_port, cell, data ):
    outb(f, base_port, cell)
    outb(f, base_port + 1, data)
#fn write_byte_to_cell(f: &mut fs::File, base_port: u16, cell: u8, data: u8) -> Result<()> {
#    outb(f, base_port, cell)?;
#    outb(f, base_port + 1, data)
#}

def write_colour(file, base_port, cell_offset , data ):
    write_byte_to_cell(f, base_port, cell_offset, (data >> 24))
    write_byte_to_cell(f, base_port, cell_offset + 1, (data >> 16))
    write_byte_to_cell(f, base_port, cell_offset + 2, (data >> 8))
    write_byte_to_cell(f, base_port, cell_offset + 3, data[0]))
#fn write_colour(f: &mut fs::File, base_port: u16, cell_offset: u8, data: u32) -> Result<()> {
#    write_byte_to_cell(f, base_port, cell_offset, (data >> 24) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 1, (data >> 16) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 2, (data >> 8) as u8)?;
#    write_byte_to_cell(f, base_port, cell_offset + 3, data as u8)
#}


def run(file, base_port):

    # prepare the cmdline arguments
    red   = (int(arg.red,   base=16) & 0x00000000).to_bytes(4,'litte')
    green = (int(arg.green, base=16) & 0x00000000).to_bytes(4,'litte')
    blue  = (int(arg.blue,  base=16) & 0x00000000).to_bytes(4,'litte')

    step_duration = args.stepduration

    invert_red   = False if not "r" in args.invhalf else True
    invert_green = False if not "g" in args.invhalf else True
    invert_blue  = False if not "b" in args.invhalf else True

    fade_in_red   = False if not "r" in args.fade_in else True
    fade_in_green = False if not "g" in args.fade_in else True
    fade_in_blue  = False if not "b" in args.fade_in else True

    # Check if indeed a NCT6795D
    if not args.ignorecheck:
        outb(f, base_port, REG_DEVID_MSB)
        msb = inb(f, base_port + 1)
        outb(f, base_port, REG_DEVID_LSB)
        ident = (msb[0]) << 8 | inb(f, base_port + 1)[:1]
        if args.verbose:
            print("Chip identifier is: {:x}".format(ident))
        if not (&{ident & 0xFFF0}) in args.valid_masks:
            raise Exception (    
                                "--ignorecheck flag, which would skip the check;
                                is not specified (may be dangerous);
                                also try --base-port"
                            )
            raise Exception (
                                "The sI/O chip identifies as {:x}, which does not
                                 seem to be NCT6795D".format(ident)
                            )

    # Without this pulsing does not work
    outb(f, base_port, 0x07)
    outb(f, base_port + 1, 0x09)
    outb(f, base_port, 0x2c)
    c = inb(f, base_port + 1)
    if c & 0x10 != 0x10 :
        outb(f, base_port + 1, c | 0x10)

    # Select the 0x12th bank.
    outb(f, base_port, 0x07)
    outb(f, base_port + 1, RGB_BANK)

    # Check if RGB control enabled?
    outb(f, base_port, 0xe0)
    d = inb(f, base_port + 1)

    if d & 0xe0 != 0xe0 :
        outb(f, base_port + 1, 0xe0 | (d & !0xe0))
    if args.disable:
        e4_val=1
    elif args.pulse:
        e4_val=0b1000
    elif not args.blink == 0:
        e4_val=(args.blink + 1) & 0b111
    else:
        e4_val=0

    write_byte_to_cell(f, base_port, 0xe4, e4_val)
    write_byte_to_cell(f, base_port, 0xfe, step_duration[0])

    ff_fade_in_val = ~0b0
    if "b" in args.fade_in:
        ff_fade_in_val = ~0b10000000 & ff_fade_in_val
    if "g" in args.fade_in:
        ff_fade_in_val = ~0b01000000 & ff_fade_in_val
    if "r" in args.fade_in:
        ff_fade_in_val = ~0b00100000 & ff_fade_in_val
    ff_fade_in_val = 0b11100000u8 & ff_fade_in_val # no fading in at all.
#    let ff_fade_in_val = 0b11100000u8 & // no fading in at all.
#        if fade_in.contains(&"b") { !0b10000000 } else { !0 } &
#        if fade_in.contains(&"g") { !0b01000000 } else { !0 } &
#        if fade_in.contains(&"r") { !0b00100000 } else { !0 };

    ff_invert_val = 0b0
    if "b" in args.invert_val:
        ff_invert_val = 0b00010000 & ff_invert_val
    if "g" in args.invert_val:
        ff_invert_val = 0b00001000 & ff_invert_val
    if "r" in args.invert_val:
        ff_invert_val = 0b00000100 & ff_invert_val
#    let ff_invert_val = 0u8 |
#        if invs.contains(&"b") { 0b00010000 } else { 0 } |
#        if invs.contains(&"g") { 0b00001000 } else { 0 } |
#        if invs.contains(&"r") { 0b00000100 } else { 0 } ;




    ff_val = (step_duration >> 8).to_bytes(1,'little') \
        & 1 | 0b10 | ff_invert_val | ff_fade_in_val
    # (step_duration >> 8) as u8 & 0b1 | // The extra bit for step duration
    #  0b10 | // if 0 disable lights on rgb header only, not on board

    write_byte_to_cell(f, base_port, 0xff, ff_val)

    write_colour(f, base_port, REDCELL, red)
    write_colour(f, base_port, GREENCELL, green)
    write_colour(f, base_port, BLUECELL, blue)

def print_all(file,base_port):
    for bank,s,e in [
                        (RGB_BANK,  0xd0,   0x1000),
                        (0x09,      0x20,   0x40),
                        (0x0b,      0x60,   0x70),
                    ]
        print("Bank {:02x} ({:02x}...{:02x}):".format(bank, s, e)
        outb(f, base_port, 0x07)
        outb(f, base_port + 1, bank)
        for x in range(101,116):
            x = x.to_bytes(1,"little")
            outb(f, base_port, x)
            d = inb(f, base_port + 1)
            if x & 0xf == 0xf :
                print("{:02x}", d)
            else:
                print!("{:02x} ", d)

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

def run_wrap():
    """
    Wrapper which enables and disables the advanced mode
    """
    base_port=args.baseport.to_bytes(2,"little")
    global file
    open_device()
    try:
        outb(file, base_port, 0x87)
    except:
        raise Exception("could not enable advanced mode")

    # These are something the built-in app does during initialization…
    # Purpose unclear
    outb(file, base_port, 0x07)
    outb(file, base_port + 1, 0x0B)
    outb(file, base_port, 0x60)
    a=inb(file, base_port + 1)
    outb(file, base_port, 0x61)
    b = inb(file, base_port + 1)

    print("{:x} {:x}", a, b)

    if arg.verbose:
        print_all(file, base_port)

    r = run(file, base_port, matches)
    # Disable the advanced mode.
    try:
        outb( file, base_port, 0xAA)
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

if __name__=='__main__':
    parse_args()
    run_wrap()
    
    
# vim: set syntax=python :

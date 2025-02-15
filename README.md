Utility for controlling RGB header on MSI boards

!WARNING! Beware it's not done yet!

v0.1.0_alpha

ported to python, probably non working yet

Needs adjustments to work with other os,
but this should be a quick fix as python is very portable. 

orignal coder:
[How this utility came to be](http://kazlauskas.me/entries/i-reverse-engineered-a-motherboard.html)

This ported utility is  only linux yet,
...it also is much more flexible than
the 7 colours MSI’s own Gaming App. Futhermore, unlike the MSI’s utility, this does not make your
system vulnerable to anybody who cares to fiddle around the system.

* Linux (/dev/port, might work on WSL?) or FreeBSD (/dev/io);
* Only MSI motherboards with NCT6795D super I/O chip;
  * Run a recent version of sensors-detect to check if you have this chip;
* No warranty whatsoever (read the license);
  * If you find your board misbehaving, try clearing CMOS;

# Working boards

This is a list of reportedly working motherboards. If the tool works on your motherboard and it is
not listed here, consider filling an issue or writing me an email and I’ll add it here.

* B350 MORTAR ARCTIC
* B350 PC MATE
* B350 TOMAHAWK
* B360M GAMING PLUS
* B450 GAMING PLUS AC
* B450 MORTAR
* B450 TOMAHAWK
* H270 MORTAR ARCTIC
* H270 TOMAHAWK ARCTIC
* X470 GAMING PLUS
* X470 GAMING PRO
* Z270 GAMING M7
* Z270 SLI PLUS
* Z370 MORTAR
* Z370 PC PRO

If your board is not working, and your motherboard is not [on this
list](https://github.com/nagisa/msi-rgb/issues?q=is%3Aissue+is%3Aopen+label%3Aboard), a new issue
would be greatly appreciated.

# How to install and run

Beware it's untested, and needs fixes.
It could eat the cat.

Do install gentoo linux, further instruction on
[gentoo](gentoo.org)
Add the ebuild to your overlay or clone mine.
Then use the package management system.

OR:
	Just copy/download the msirgbpy.py file.
	Run it with python3.


There you get original one:

```
git clone https://github.com/nagisa/msi-rgb
cd msi-rgb
cargo build --release
```

FURTHER DOWN HERE , THE DESCRIPTION PROBABLY NOT APPLIES ANYMORE.

FIXME

You’ll need root to run this program:

```
sudo ./target/release/msi-rgb 00000000 FFFFFFFF 00000000 # for green
```

The hexa numbers represent each color as a sequence *in time* per byte so 4 change of colors.

```
sudo ./target/release/msi-rgb FF000000 00FF0000 0000FF00 # this makes red then green then blue then off then red etc..
```

Run following for more options:

```
./target/release/msi-rgb -h
```

# Examples

## Heartbeat

```
sudo ./target/release/msi-rgb 206487a9 206487a9 10325476 -ir -ig -ib -d 5
```

[![animation of pulse](https://thumbs.gfycat.com/BlueWhichAntbear-size_restricted.gif)](https://gfycat.com/BlueWhichAntbear)

## Police

```
sudo ./target/release/msi-rgb -d15 FF00FF00 0 00FF00FF
```

[![animation of police](https://thumbs.gfycat.com/RemoteChiefBobolink-size_restricted.gif)](https://gfycat.com/RemoteChiefBobolink)

## Happy Easter

[From colourlovers](http://www.colourlovers.com/palette/4479254/Happy-Easter-2017!)

```
sudo ./target/release/msi-rgb 58e01c0d 504fdcb9 e4aa75eb --blink 2 -d 32
```

[![animation of happyeaster](https://thumbs.gfycat.com/DirectBleakBuzzard-size_restricted.gif)](https://gfycat.com/DirectBleakBuzzard)

## Hue wheel (t HUE, 0.9 SATURATION, 1.0 VALUE) (REQUIRES PYTHON)

![animation of hue wheel](https://thumbs.gfycat.com/ViciousGreenBittern-size_restricted.gif)

```
echo -e "import colorsys, time, subprocess\ni=0\nwhile True:\n  subprocess.call(['target/release/msi-rgb', '-d511'] + list(map(lambda x: ('{0:01x}'.format(int(15*x)))*8, colorsys.hsv_to_rgb((i % 96.0) / 96.0, 0.9, 1))))\n  time.sleep(0.1)\n  i+=1" | sudo python -
```

# License

Code is licensed under the permissive ISC license. If you create derivative works and/or nice RGB
schemes, I would love to see them :)

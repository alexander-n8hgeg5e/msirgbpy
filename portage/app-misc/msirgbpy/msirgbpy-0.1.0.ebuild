# Copyright 1999-2018 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
EAPI=7


PYTHON_COMPAT=( python3_{6,7} )
EGIT_REPO_URI="${CODEDIR}/${PN} ${MYGITHUB_URIBASE}${PN}.git"
inherit git-r3

DESCRIPTION="python port of msi-rgb, linux only"
HOMEPAGE=""

LICENSE="ISC"
SLOT="0"
KEYWORDS="~amd64 ~x86"
IUSE=""

DEPEND=""
RDEPEND="
dev-lang/python:3
virtual/linux-sources
"

src_install(){
	dobin msirgbpy
}

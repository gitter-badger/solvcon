import os
import sys
from solvcon import __version__

# compilation.
AddOption('--disable-openmp', dest='use_openmp',
    action='store_false', default=True,
    help='Disable OpenMP.')
AddOption('--cc', dest='cc', type='string', action='store', default='gcc',
    help='C compiler (SCons tool): gcc, intelc.',)
AddOption('--optlevel', dest='optlevel', type=int, action='store', default=2,
    help='Optimization level; default is 2.',)
AddOption('--cmpvsn', action='store', default='', dest='cmpvsn',
    help='Compiler version; for gcc-4.5 it\'s --cmpvsn=-4.5',
)
AddOption('--sm', action='store', default='20', dest='sm',
    help='Compute capability; 13=1.3 and 20=2.0 are currently supported.',
)

# dependencies and patches.
AddOption('--download', dest='download',
    action='store_true', default=False,
    help='Flag to download external packages.')
AddOption('--extract', dest='extract',
    action='store_true', default=False,
    help='Flag to extract external packages.')
AddOption('--apply-patches', dest='patches',
    action='store', default='',
    help='Indicate matches to be applied.')

AddOption('--get-scdata', dest='get_scdata',
    action='store_true', default=False,
    help='Flag to clone/pull example data.')

AddOption('--count', dest='count',
    action='store_true', default=False,
    help='Count line of sources.')

class Archive(object):
    """
    External package downloader/extractor.
    """

    bufsize = 1024*1024
    depdir = 'dep'

    pkgs = (
        ('http://glaros.dtc.umn.edu'
         '/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz',
         'd3848b454532ef18dc83e4fb160d1e10'),
    )

    def __init__(self, url, md5sum, filename=None):
        import os
        from urlparse import urlparse
        if isinstance(url, basestring):
            self.url = [url]
        else:
            self.url = url
        self.md5sum = md5sum
        if filename == None:
            up = urlparse(self.url[0])
            filename = up[2].split('/')[-1]
        self.filename = os.path.join(self.depdir, filename)
        if not os.path.exists(self.depdir):
            os.makedirs(self.depdir)

    @classmethod
    def digest(cls, f):
        import hashlib
        m = hashlib.md5()
        while True:
            data = f.read(cls.bufsize)
            m.update(data)
            if len(data) < cls.bufsize: break
        return m.hexdigest()

    def download(self):
        import sys
        import os
        import urllib
        url = self.url
        fn = self.filename
        cksum = self.md5sum
        if os.path.exists(fn):
            if cksum and cksum != self.digest(open(fn, 'rb')):
                sys.stdout.write("%s checksum mismatch, delete old.\n" % fn)
                os.unlink(fn)
            else:
                sys.stdout.write("%s exists.\n" % fn)
                return False
        # download.
        for curl in url:
            sys.stdout.write("Download %s from %s: " % (fn, curl))
            sys.stdout.flush()
            try:
                uf = urllib.urlopen(curl)
            except IOError:
                sys.stdout.write("failed\n")
                continue
            else:
                break
        f = open(fn, 'wb')
        sys.stdout.flush()
        while True:
            data = uf.read(self.bufsize)
            sys.stdout.write('.')
            sys.stdout.flush()
            f.write(data)
            if len(data) < self.bufsize: break
        uf.close()
        f.close()
        # checksum.
        if cksum:
            if cksum != self.digest(open(fn, 'rb')):
                sys.stdout.write("note, %s checksum mismatch!\n" % fn)
            else:
                sys.stdout.write("%s checksum OK.\n" % fn)
        else:
            sys.stdout.write("no checksum defined for %s .\n" % fn)
        sys.stdout.write(" done.\n")

    def extract(self):
        import tarfile
        tar = tarfile.open(self.filename)
        tar.extractall(path=self.depdir)
        tar.close()

    @classmethod
    def downloadall(cls):
        for url, md5sum in cls.pkgs:
            obj = Archive(url, md5sum)
            obj.download()

    @classmethod
    def extractall(cls):
        for url, md5sum in cls.pkgs:
            obj = Archive(url, md5sum)
            obj.extract()

class LineCounter(object):
    """
    Walk given directory to count lines in source files.
    """

    def __init__(self, *args, **kw):
        self.exts = args
        self.counter = dict()
        self.testdir = kw.pop('testdir', ['tests'])
        self.testcounter = 0
        self.corecounter = 0

    def __call__(self, path):
        import os
        from os.path import join, splitext
        for root, dirs, files in os.walk(path):
            for fname in files:
                mainfn, extfn = splitext(fname)
                if extfn not in self.exts:
                    continue
                if os.path.islink(join(root, fname)):
                    continue
                nline = len(open(join(root, fname)).readlines())
                self.counter[extfn] = self.counter.get(extfn, 0) + nline
                if os.path.basename(root) in self.testdir:
                    self.testcounter += nline
                else:
                    if extfn == '.py' and os.path.basename(root) == 'solvcon':
                        self.corecounter += nline

    def __str__(self):
        keylenmax = max([len(key) for key in self.counter])
        tmpl = "%%-%ds = %%d" % keylenmax
        all = 0
        ret = list()
        for extfn in sorted(self.counter.keys()):
            ret.append(tmpl % (extfn, self.counter[extfn]))
            all += self.counter[extfn]
        ret.append(tmpl % ('All', all))
        ret.append('%d are for unittest.' % self.testcounter)
        ret.append('%d are for core (only .py directly in solvcon/).' % \
            self.corecounter)
        return '\n'.join(ret)

if GetOption('download'):
    Archive.downloadall()
if GetOption('extract'):
    Archive.extractall()

patches = [token for token in GetOption('patches').split(',') if token]
for patch in patches:
    patchpath = os.path.join('patch', patch+'.patch')
    os.system('patch -p0 -i %s'%patchpath)

if GetOption('count'):
    counter = LineCounter('.py', '.c', '.h', '.cu')
    paths = ('solvcon', 'src', 'include', 'test')
    for path in paths:
        counter(path)
    sys.stdout.write('In directories %s:\n' % ', '.join(paths))
    sys.stdout.write(str(counter)+'\n')
    sys.exit(0)

# metis environment.
metisenv = Environment(ENV=os.environ,
    tools=[
        'mingw' if sys.platform.startswith('win') else 'default',
        GetOption('cc'),
    ], CFLAGS='-O2')

# solvcon environment.
env = Environment(ENV=os.environ)
# tools.
env.Tool('mingw' if sys.platform.startswith('win') else 'default')
env.Tool(GetOption('cc'))
env.Tool('solvcon')
env.Tool('sphinx')
env.Tool('scons_epydoc')
# Intel C runtime library.
if GetOption('cc') == 'intelc':
    env.Append(LIBS='irc_s')
# optimization level.
env.Append(CFLAGS='-O%d'%GetOption('optlevel'))
# SSE4.
if env.HasSse4() and GetOption('cc') == 'gcc':
    env.Append(CFLAGS='-msse4')
    env.Append(CFLAGS='-mfpmath=sse')
# OpenMP.
if GetOption('use_openmp'):
    if GetOption('cc') == 'gcc':
        env.Append(CFLAGS='-fopenmp')
        env.Append(LINKFLAGS='-fopenmp')
    elif GetOption('cc') == 'intelc':
        env.Append(CFLAGS='-openmp')
        env.Append(LINKFLAGS='-openmp')
# include paths.
env.Append(CPPPATH='include')
# CUDA.
env.Tool('cuda')
env.Append(NVCCFLAGS='-arch=sm_%s'%GetOption('sm'))
env.Append(NVCCINC=' -I include')

# replace gcc with a certain version.
if GetOption('cc') == 'gcc':
    env.Replace(CC='gcc%s'%GetOption('cmpvsn'))

# get example data.
if GetOption('get_scdata'):
    if __version__.endswith('+'):
        env.GetScdata('https://bitbucket.org/solvcon/scdata', 'scdata')
    else:
        raise RuntimeError('released tarball shouldn\'t use this option')

everything = []
Export('everything', 'env', 'metisenv')

SConscript(['SConscript'])
Default(everything)

# vim: set ft=python ff=unix:

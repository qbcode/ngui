#! /usr/bin/env python
# encoding: utf-8

from waflib import Scripting, Logs, Options, Errors
from waflib.Errors import WafError

def try_git_version():
    import os
    import sys

    version = None
    try:
        #version = os.popen('git describe --always --dirty --long').read().strip().strip("v")
		version = os.popen('./build-aux/git-version-gen .tarball-version').read()
    except Exception as e:
        print e
    return version

# the following two variables are used by the target "waf dist"
APPNAME="qbdevice"
VERSION = try_git_version()
out = 'build'

def options(opt):
	opt.load('compiler_cxx compiler_c gnu_dirs waf_unit_test')
	opt.load('coverage boost daemon', tooldir=['./waftools/'])
	opt.add_option('--onlytests', action='store_true', default=True, help='Exec unit tests only', dest='only_tests')

	opt.add_option('--lcov-report',
			help=('Generate a code coverage report '
				'(use this option at build time, not in configure)'),
			action="store_true", default=False,
			dest='lcov_report')

def configure(conf):
    # load these things from waf
	conf.load('compiler_cxx compiler_c gnu_dirs waf_unit_test')

	# check for these libraries that we depend on
	#conf.check_cfg( package='libgflags', 
	#		uselib_store='GFLAGS',
	#		args=['libgflags >= 2.0', 'libgflags < 2.1', '--cflags', '--libs'],
	#		msg=r"Checking for 'libgflags' 2.0")
	#conf.check_cfg( package='libglog', uselib_store='GLOG', args=['--cflags', '--libs'], atleast_version='0.3.3' )
	conf.check_cfg( package='sdl2', uselib_store='SDL2', args=['--cflags', '--libs'], atleast_version='2.0'  )

	# make sure these command line utils are around as helpers
	conf.find_program('dpkg-buildpackage', mandatory=False)
	conf.find_program("sphinx-build", var="SPHINX_BUILD")
	conf.find_program("lcov", mandatory=False)
	conf.find_program("genhtml", mandatory=False)

	# check at least for these headers which are used
	conf.check(header_name='string' )
	conf.check(header_name='stdbool.h' )
	conf.check(header_name='iostream' )
	conf.check(header_name='time.h')
	conf.check(header_name='stdio.h')
	conf.check(header_name='string.h')
	conf.check(header_name='limits.h')
	conf.check(header_name='stdint.h')

	# check for system libraries that we need
	conf.check(header_name='zlib.h')
	conf.check(lib='z', uselib_store='Z')
	conf.check(header_name='pthread.h')
	conf.check(lib='pthread', uselib_store='PTHREAD')

	conf.env.VERSION = VERSION
	conf.env.APPNAME = APPNAME

	#git_version = try_git_version()

	#if git_version:
	#	conf.env.VERSION += '-' + git_version

	conf.define('VERSION', VERSION)
	conf.define('PACKAGE_STRING', APPNAME)
	conf.define('BINDIR', conf.env['BINDIR'])

	conf.env.append_unique('LDFLAGS', '-static')
	conf.env.append_unique('CFLAGS', '-g')
	conf.env.append_unique('CXXFLAGS', '-g')

	conf.write_config_header('src/qbshare/config.h')

def build(bld):
	bld.env.VERSION = VERSION
	bld.add_post_fun(gtest_results)
	#bld.options.all_tests = True

	if Options.options.lcov_report:
		lcov_report(bld)

	bld.recurse('src/gmock src/ngui')

def dist(ctx):
	ctx.base_name = APPNAME + "_" + VERSION
	ctx.excl = ' **/.waf-1* **/*~ **/*.pyc **/*.swp **/.lock-w* **/.git build'
	ctx.algo = 'tar.bz2'

def gtest_results(bld):
    lst = getattr(bld, 'utest_results', [])
    if not lst:
        return
    for (f, code, out, err) in lst:
        # if not code:
        #     continue

        # uncomment if you want to see what's happening
        # print(str(out).encode('utf-8'))
        output = str(out).encode('utf-8').split('\n')
        for i, line in enumerate(output):
            if '[ RUN      ]' in line and code:
                i += 1
                if '    OK ]' in output[i]:
                    continue
                while not '[ ' in output[i]:
                    Logs.warn('%s' % output[i])
                    i += 1
            elif ' FAILED  ]' in line and code:
                Logs.error('%s' % line)
            elif ' PASSED  ]' in line:
                Logs.info('%s' % line)

def lcov_report(bld):
    import os
    import subprocess

    env = bld.env

    if not env['GCOV']:
        raise WafError("project not configured for code coverage;"
                       " reconfigure with --with-coverage")

    os.chdir(out)
    try:
        lcov_report_dir = 'lcov-report'
        create_dir_command = "rm -rf " + lcov_report_dir
        create_dir_command += " && mkdir " + lcov_report_dir + ";"

        if subprocess.Popen(create_dir_command, shell=True).wait():
            raise SystemExit(1)

        info_file = os.path.join(lcov_report_dir, 'report.info')
        lcov_command = "lcov -c -d . -o " + info_file
        lcov_command += " -b " + os.getcwd()
        if subprocess.Popen(lcov_command, shell=True).wait():
            raise SystemExit(1)

        genhtml_command = "genhtml --no-branch-coverage -o " + lcov_report_dir
        genhtml_command += " " + info_file
        if subprocess.Popen(genhtml_command, shell=True).wait():
            raise SystemExit(1)
    finally:
        os.chdir("..")

/*
 * checker.h - VMchecker header file
 *
 * (C) 2008 Adriana Szekeres <aaa_sz@yahoo.com>
 * coding issues, Razvan Deaconescu <razvan@rosedu.org>
 */

#ifndef CHECKER_H_
#define CHECKER_H_	1

#include <time.h>
#include <string>

using namespace std;

/* define run timeout */
#define TIMEOUT		120

/*define file names */

#define CHECKER_FILE		"file.zip"
#define CHECKER_TEST		"tests.zip"
#define BUILD_SCRIPT		"build.sh"
#define RUN_SCRIPT		"run.sh"
#define LOCAL_SCRIPT		"local.sh"
#define BUILD_OUTPUT_FILE	"job_build"
#define RUN_OUTPUT_FILE		"job_run"
#define ERROR_OUTPUT_FILE	"job_errors"
#define RESULT_OUTPUT_FILE	"job_results"
#define KMESSAGE_OUTPUT_FILE	"job_km"

#endif

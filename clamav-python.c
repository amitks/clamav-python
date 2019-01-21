#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <clamav.h>
#include <Python.h>

#define CL_POSITIVE 1
#define CL_NEGATIVE 0

#define UNUSED(expr) do { (void)(expr); } while (0)

struct cl_engine *engine ;
static char *scan_buff(const char *data, int length);
static char *scan_file(const char *file_path);

void exit_cleanup(void){
    if (engine != NULL)
        cl_engine_free(engine);
}

/* clamav signature compile logic */
static PyObject * compile(PyObject *self, PyObject *args, PyObject *keywords)
{
    static char *kwlist[] = {"sig_path", NULL};
    const char *sig_path = NULL;
    const char *dbDir = cl_retdbdir();
    Py_ssize_t length = 0;

    /* this makes sure multiple compile does not do memory leak.*/
    exit_cleanup();

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "s#", kwlist, &sig_path, &length))
    {
        printf("Invalid sig path! using default.\n");
    }

    if (sig_path != NULL)
        dbDir = sig_path;

#ifdef DEBUG
    printf("DEBUG: using signature path: '%s'\n", dbDir);
#endif

    if (CL_SUCCESS == cl_init(CL_INIT_DEFAULT)) {
        
        unsigned int signatureNum = 0;
        engine = cl_engine_new();
        if (CL_SUCCESS == cl_load(dbDir, engine, &signatureNum, CL_DB_STDOPT) &&
            CL_SUCCESS == cl_engine_compile(engine)) {
#ifdef DEBUG
            printf("DEBUG: engine loaded with signatures..\n");
#endif
        }
        else {
            PyErr_SetString(PyExc_ValueError, "Invalid clamav signature!");
            return NULL;
        }
    }
    
    Py_RETURN_NONE;
}

/* scans byte-stream or file data after compiling signatures */
static PyObject *scan(PyObject *self, PyObject *args, PyObject *keywords)
{
    if (engine == NULL) {
        printf("please compile before running scan..");
        Py_RETURN_NONE;
    }
    static char *kwlist[] = {"data", "file_path", NULL};
    const char *data = NULL;
    const char *file_path = NULL;
    Py_ssize_t length = 0;
    Py_ssize_t n = 0;
    char *sig = NULL;
    int N = 0; /* initial list size for signature match */
    PyObject *signature_list = PyList_New(N);

    if (PyArg_ParseTupleAndKeywords(args, keywords, "|s#s#", kwlist, &data, &length, &file_path, &n))
    {
        if (data == NULL && file_path == NULL)
            return NULL;
    }

#ifdef DEBUG
    printf("DEBUG: file_path: %s \n", file_path);
#endif

    if (data != NULL) {
        sig = scan_buff(data, length);

#ifdef DEBUG
        printf("DEBUG: signature match: %s \n", sig);
#endif
        if (sig != NULL) {
            PyObject *python_string = Py_BuildValue("s", sig);
            PyList_Append(signature_list, python_string);
        }
        return signature_list;
    }

    if (file_path != NULL) {
        sig = scan_file(file_path);

#ifdef DEBUG
        printf("DEBUG: signature match: %s \n", sig);
#endif
        if (sig != NULL) {
            PyObject* python_string = Py_BuildValue("s", sig);
            PyList_Append(signature_list, python_string);
        }
        return signature_list;
    }

    Py_RETURN_NONE;
}

static PyMethodDef clamavMethods[] = {
    {"compile",(PyCFunction) compile, METH_VARARGS | METH_KEYWORDS},
    {"scan",(PyCFunction) scan, METH_VARARGS | METH_KEYWORDS},
    {NULL, NULL, 0, NULL}
};

#if 0
static PyMethodDef clamavMethods2[] = {
    {"scan",(PyCFunction) scan, METH_VARARGS | METH_KEYWORDS},
    {NULL, NULL, 0, NULL}
};
#endif

PyMODINIT_FUNC
initclamav(void)
{
    (void) Py_InitModule("clamav", clamavMethods);
    Py_AtExit(exit_cleanup);
}

static char *scan_buff(const char *buffer, int len)
{
    const char *virusName = NULL;
    long unsigned int scanned = 0;
    virusName = NULL;
    cl_fmap_t *map = cl_fmap_open_memory(buffer, len);
    int scanRet = cl_scanmap_callback(map, &virusName, &scanned, engine, CL_SCAN_STDOPT, NULL);

    UNUSED(scanRet);
#ifdef DEBUG
    switch (scanRet) {
        case CL_VIRUS:
            printf("DEBUG: [X]  %s -> %s is_mal: %d\n", buffer, virusName, CL_VIRUS);
            break;
        case CL_CLEAN:
            printf("DEBUG: [O]  %s -> %s is_mal: %d\n", buffer, virusName, CL_CLEAN);
            break;
        default:
            printf("DEBUG: [U]  %s -> %s is_mal: %d\n", buffer, virusName, CL_CLEAN);
    }
#endif
    return (char *)virusName;
}

static char *scan_file(const char *file_path)
{
    const char *virusName = NULL;
    long unsigned int scanned = 0;
    virusName = NULL;
    int scanRet = cl_scanfile(file_path, &virusName, &scanned, engine, CL_SCAN_STDOPT);

    UNUSED(scanRet);
#ifdef DEBUG
    switch (scanRet) {
        case CL_VIRUS:
            printf("DEBUG: [X]  %s -> %s is_mal: %d\n", file_path, virusName, CL_VIRUS);
            break;
        case CL_CLEAN:
            printf("DEBUG: [O]  %s -> %s is_mal: %d\n", file_path, virusName, CL_CLEAN);
            break;
        default:
            printf("DEBUG: [U]  %s -> %s is_mal: %d\n", file_path, virusName, CL_CLEAN);
    }
#endif
    return (char *)virusName;
}



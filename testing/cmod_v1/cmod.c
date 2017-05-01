#include <Python.h>

static PyObject* _hello_world(PyObject* self) {
    return PyUnicode_FromString("hello world");
}

static struct PyMethodDef methods[] = {
    {"hello_world", (PyCFunction)_hello_world, METH_NOARGS},
    {NULL, NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "cmod",
    NULL,
    -1,
    methods
};

PyMODINIT_FUNC PyInit_cmod(void) {
    return PyModule_Create(&module);
}
#else
PyMODINIT_FUNC initcmod(void) {
    Py_InitModule3("cmod", methods, NULL);
}
#endif

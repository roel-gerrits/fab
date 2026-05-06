#include <cstdio>

#include "lib.h"

#include "liba.h"

class Test {
public:
  Test() { printf("Test()\n"); }
  ~Test() { printf("~Test() \n"); }
};

auto main() -> int {

  Test t;

  void *test = NULL;

  printf("hello from main.cpp\n");
  libfunc1();
  libafunc();
}

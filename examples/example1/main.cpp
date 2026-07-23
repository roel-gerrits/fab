#include <cstdio>

#include "lib.h"
#include "liba.h"

class Test {
public:
  Test() { printf("Test()\n"); }
  ~Test() { printf("~Test() \n"); }
};

// auto main() -> int {
// int main() {
auto main() -> int {

  Test t;



  void *test = nullptr;

  printf("hello from main.cpp\n");
  libfunc1();
  printf("arch: %s\n", __linux__);


  libafunc();
}

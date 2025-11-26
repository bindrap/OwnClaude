// Fibonacci sequence program in C++
#include <iostream>

int fibonacci(int n) {
    if (n <= 0) return 0;
    else if (n == 1) return 1;
    else return fibonacci(n-1) + fibonacci(n-2);
}

int main() {
    int num; std::cout << "Enter a number: "; std::cin >> num;
    std::cout << "Fibonacci number at position " << num << ": " << fibonacci(num);
    return 0;
}

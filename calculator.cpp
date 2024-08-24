#include <iostream>
#include <stdexcept>

using namespace std;

void add(double num1, double num2) {
    cout << "Result: " << num1 + num2 << endl;
}

void subtract(double num1, double num2) {
    cout << "Result: " << num1 - num2 << endl;
}

void multiply(double num1, double num2) {
    cout << "Result: " << num1 * num2 << endl;
}

void divide(double num1, double num2) {
    if (num2 == 0) {
        throw runtime_error("Error! Division by zero.");
    } else {
        cout << "Result: " << num1 / num2 << endl;
    }
}

int main() {
    int choice;
    double num1, num2;

    cout << "Select operation:" << endl;
    cout << "1. Add" << endl;
    cout << "2. Subtract" << endl;
    cout << "3. Multiply" << endl;
    cout << "4. Divide" << endl;

    cout << "Enter choice (1/2/3/4): ";
    cin >> choice;

    if (cin.fail() || choice < 1 || choice > 4) {
        cout << "Invalid input" << endl;
        return 1;
    }

    cout << "Enter first number: ";
    cin >> num1;

    if (cin.fail()) {
        cout << "Invalid input" << endl;
        return 1;
    }

    cout << "Enter second number: ";
    cin >> num2;

    if (cin.fail()) {
        cout << "Invalid input" << endl;
        return 1;
    }

    try {
        switch (choice) {
            case 1:
                add(num1, num2);
                break;
            case 2:
                subtract(num1, num2);
                break;
            case 3:
                multiply(num1, num2);
                break;
            case 4:
                divide(num1, num2);
                break;
            default:
                cout << "Invalid choice" << endl;
        }
    } catch (const runtime_error& e) {
        cout << e.what() << endl;
    }

    return 0;
}

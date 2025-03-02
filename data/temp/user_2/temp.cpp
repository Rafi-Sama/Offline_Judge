#include <iostream>
#include <cmath>
using namespace std;
 
int main() {
    int matrix[5][5];
    for (int i = 0; i < 5; ++i) {
        for (int j = 0; j < 5; ++j) {
            cin >> matrix[i][j];
        }
    }
    int row_of_one, col_of_one;
    for (int i = 0; i < 5; ++i) {
        for (int j = 0; j < 5; ++j) {
            if (matrix[i][j] == 1) {
                row_of_one = i;
                col_of_one = j;
                break;
            }
        }
    }
    int moves = abs(2 - row_of_one) + abs(2 - col_of_one);
 
    cout << moves << endl;
    return 0;
}
#include <bits/stdc++.h>
#define all(x) x.begin(), x.end()
#define endl '\n'
#define yes cout << "YES" << endl
#define no cout << "NO" << endl

using namespace std;

void solve()
{
    int n, m, k;
    cin >> n >> m;

    vector<int> v(n);

    for (auto &i : v)
        cin >> i;

    cin >> k;

    v[0] = min(v[0], k - v[0]);

    for (int i = 1; i < n; i++)
    {
        int mn = min(v[i], k - v[i]);

        if (mn >= v[i - 1])
        {
            v[i] = mn;
        }
        else
        {
            int mx = max(v[i], k - v[i]);
            if (mx >= v[i - 1])
            {
                v[i] = mx;
            }
            else
            {
                cout << "NO" << endl;
                return;
            }
        }
    }

    cout << "YES" << endl;
}

int main()
{
    ios_base::sync_with_stdio(0);
    cin.tie(0);
    solve();
    return 0;
}
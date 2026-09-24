using UnityEngine;

namespace Fixture.Game
{
    public sealed class Health : MonoBehaviour
    {
        public int Current { get; private set; }

        public void Initialize(int max) { Current = max; }

        public void TakeDamage(int amount)
        {
            Current = Mathf.Max(0, Current - amount);
        }
    }
}

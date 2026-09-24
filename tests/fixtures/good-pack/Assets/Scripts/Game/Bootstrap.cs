using UnityEngine;

namespace Fixture.Game
{
    public sealed class Bootstrap : MonoBehaviour
    {
        [SerializeField] private Health _player;

        private void Awake()
        {
            _player.Initialize(100);
        }
    }
}

using UnityEngine;

namespace LiverAR
{
    public class TouchModelInteractor : MonoBehaviour
    {
        float initialDistance;
        Vector3 initialScale;

        void Update()
        {
            if (Input.touchCount == 1)
            {
                var delta = Input.GetTouch(0).deltaPosition;
                transform.parent.Rotate(Vector3.up, -delta.x * 0.2f, Space.World);
            }
            if (Input.touchCount == 2)
            {
                var a = Input.GetTouch(0).position;
                var b = Input.GetTouch(1).position;
                var distance = Vector2.Distance(a, b);
                if (Input.GetTouch(1).phase == TouchPhase.Began) { initialDistance = distance; initialScale = transform.parent.localScale; }
                if (initialDistance > 0f) transform.parent.localScale = initialScale * Mathf.Clamp(distance / initialDistance, 0.2f, 5f);
            }
        }
    }
}

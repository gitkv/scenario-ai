using UnityEngine;
using System.Collections;

[RequireComponent(typeof(CharacterController))]
public class RandomMovement : MonoBehaviour
{
    public float moveRadius = 5.0f;
    public float moveSpeed = 1.0f;
    public float waitTime = 2.0f;
    public float rotationSpeed = 2.0f;
    private Vector3 initialPosition;
    private Vector3 nextPosition;
    private CharacterController characterController;
    private float lerpTime = 0f;

    private void Start()
    {
        initialPosition = transform.position;
        characterController = GetComponent<CharacterController>();
        StartCoroutine(MoveRoutine());
    }

    private IEnumerator MoveRoutine()
    {
        while (true)
        {
            SetNextPosition();

            // Вычисляем время, необходимое для перемещения к следующей позиции
            lerpTime = Vector3.Distance(transform.position, nextPosition) / moveSpeed;

            float elapsedTime = 0;
            Vector3 startingPos = transform.position;

            while (elapsedTime < lerpTime)
            {
                transform.position = Vector3.Lerp(startingPos, nextPosition, (elapsedTime / lerpTime));
                transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(nextPosition - transform.position), rotationSpeed * Time.deltaTime);
                elapsedTime += Time.deltaTime;
                yield return null;
            }

            // Пауза перед следующим движением
            yield return new WaitForSeconds(waitTime);
        }
    }

    private void SetNextPosition()
    {
        nextPosition = initialPosition + (Random.insideUnitSphere * moveRadius);
        nextPosition.y = initialPosition.y; // Чтобы персонаж не двигался вверх или вниз
    }
}

using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public enum CharacterState
{
    IDLING,
    WALKING,
    TALKING
}

public class CharacterBehaviour : MonoBehaviour
{
    [SerializeField] private Animator animator;
    [HideInInspector] public CharacterState characterState;
    [SerializeField] private float minStateTime;
    [SerializeField] private float maxStateTime;
    [SerializeField] private float walkSpeed;
    [HideInInspector] public bool talking = false;
    private Vector2 destination;
    [SerializeField] private Vector2 xLimits;
    [SerializeField] private Vector2 zLimits;
    [SerializeField] private Vector3 defaultLookLocation;
    [HideInInspector] public CharacterBehaviour talkingTo;

    // Start is called before the first frame update
    void Start()
    {
        Invoke("ChangeState", Random.Range(minStateTime, maxStateTime));
    }

    public void ToggleTalk(bool talking, CharacterBehaviour talkingTo = null)
    {
        this.talkingTo = talkingTo;
        if (this.talking && !talking)
        {
            characterState = CharacterState.IDLING;
            Invoke("ChangeState", Random.Range(minStateTime, maxStateTime));
            animator.SetBool("walking", false);
            animator.SetBool("idling", true);
            animator.SetBool("talking", false);
        }

        this.talking = talking;

        if (this.talking)
        {
            characterState = CharacterState.TALKING;

            animator.SetBool("walking", false);
            animator.SetBool("idling", false);
            animator.SetBool("talking", true);
            CancelInvoke("ChangeState");
        }
    }

    // Update is called once per frame
    void ChangeState()
    {
        if (talking)
        {
            return;
        }

        if (characterState == CharacterState.IDLING)
        {
            characterState = CharacterState.WALKING;
            animator.SetBool("walking", true);
            animator.SetBool("idling", false);
            animator.SetBool("talking", false);

            destination = new Vector2(Random.Range(xLimits.x, xLimits.y), Random.Range(zLimits.x, zLimits.y));
            Invoke("ChangeState", Random.Range(minStateTime, maxStateTime));
        }
        else if (characterState == CharacterState.WALKING)
        {
            characterState = CharacterState.IDLING;
            animator.SetBool("walking", false);
            animator.SetBool("idling", true);
            animator.SetBool("talking", false);
            Invoke("ChangeState", Random.Range(minStateTime * 2, maxStateTime * 2));
        }
    }

    private void Update()
    {
        if (characterState == CharacterState.WALKING)
        {
            Vector3 targetPosition = new Vector3(destination.x, transform.position.y, destination.y);
            Vector3 direction = targetPosition - transform.position;
            if (direction != Vector3.zero)
            {
                transform.rotation = Quaternion.Lerp(transform.rotation, Quaternion.LookRotation(direction, Vector3.up), 10f * Time.deltaTime);
            }

            transform.position = Vector3.MoveTowards(transform.position, targetPosition, walkSpeed * Time.deltaTime);
            
            if (Vector3.Distance(transform.position, targetPosition) <= 0.01f)
            {
                CancelInvoke("ChangeState");
                ChangeState();
            }
        }
        else if (characterState == CharacterState.TALKING)
        {
            Vector3 direction = defaultLookLocation - transform.position;
            if (direction != Vector3.zero)
            {
                transform.rotation = Quaternion.Lerp(transform.rotation, Quaternion.LookRotation(direction, Vector3.up), 10f * Time.deltaTime);
            }
        }
        else if (characterState == CharacterState.IDLING)
        {
            CharacterBehaviour cbTarget = ScenarioManager.instance.GetTalkingCharacter();

            if (cbTarget != null)
            {
                Vector3 direction = cbTarget.gameObject.transform.position - transform.position;
                if (direction != Vector3.zero)
                {
                    transform.rotation = Quaternion.Lerp(transform.rotation, Quaternion.LookRotation(direction, Vector3.up), 10f * Time.deltaTime);
                }
            }
        }

        if (characterState == CharacterState.TALKING && talkingTo != null)
        {
            Vector3 direction = talkingTo.gameObject.transform.position - transform.position;
            if (direction != Vector3.zero)
            {
                transform.rotation = Quaternion.Lerp(transform.rotation, Quaternion.LookRotation(direction, Vector3.up), 10f * Time.deltaTime);
            }
        }
    }

}

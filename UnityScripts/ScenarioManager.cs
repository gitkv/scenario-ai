using System.Collections;
using System.Collections.Generic;
using Unity.VisualScripting;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;
using TMPro;
using System.IO;
using UnityEngine.SceneManagement;

public class ScenarioManager : MonoBehaviour
{

    [SerializeField]
    private string serverURL = "http://localhost:5000";
    [SerializeField]
    private string iddleText = "*бездельничает*";
    [SerializeField]
    private AudioClip laterClip;
    [SerializeField]
    private GameObject laterImage;
    private StoryModel story;
    private List<AudioClip> audioClips;
    [SerializeField]
    private AudioSource dialogueSource;
    [SerializeField]
    private TextMeshProUGUI subtitles;
    [SerializeField]
    private TextMeshProUGUI requestor;
    private int scenarioProgress;
    private Dictionary<string, CharacterBehaviour> characterMap;
    [HideInInspector] public Transform cameraTarget;
    [SerializeField] private DynamicCamera dynamicCamera;
    public static ScenarioManager instance;

    private void Awake()
    {
        instance = this;
    }

    // Start is called before the first frame update
    void Start()
    {
        characterMap = new Dictionary<string, CharacterBehaviour>();
        foreach (CharacterBehaviour character in FindObjectsOfType<CharacterBehaviour>())
        {
            characterMap[character.gameObject.name] = character;
        }

        Invoke("LoadStory", 2f);
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.R))
        {
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }
    }

    void LoadStory()
    {
        StartCoroutine(GetStory());
    }


    void PlayScenario()
    {
        if (scenarioProgress < audioClips.Count)
        {
            PlayScene();
        }
        else
        {
            StartCoroutine(DeleteStory(story.id));
            Invoke("ShowLaterImageAndPlayClip", 0.5f);
        }
    }

    void ShowLaterImageAndPlayClip()
    {

        subtitles.text = "";
        requestor.text = iddleText;
        laterImage.SetActive(true);
        dialogueSource.clip = laterClip;
        dialogueSource.Play();

        Invoke("HideLaterImageAndLoadNextScenario", 4f);
    }

    void HideLaterImageAndLoadNextScenario()
    {
        laterImage.SetActive(false);

        LoadStory();
    }

    void PlayScene()
    {
        dialogueSource.clip = audioClips[scenarioProgress];
        dialogueSource.Play();

        subtitles.text = story.scenario[scenarioProgress].text;

        CharacterBehaviour cbTarget = GetCameraTarget(story.scenario[scenarioProgress].character);
        cameraTarget = cbTarget != null ? cbTarget.gameObject.transform : null;

        if (Random.Range(0, 2) == 0)
        {
            dynamicCamera.ChangeCamera();
        }

        CharacterBehaviour previousTalkingCharacter = GetTalkingCharacter();
        StopTalkAnimations(story.scenario[scenarioProgress].character);
        ToggleTalkAnimations(story.scenario[scenarioProgress].character, previousTalkingCharacter);
        scenarioProgress++;
        Invoke("PlayScenario", audioClips[scenarioProgress - 1].length + 0.5f);
    }

    CharacterBehaviour GetCameraTarget(string characterName)
    {
        if (characterMap.ContainsKey(characterName))
        {
            return characterMap[characterName];
        }

        return null;
    }

    void ToggleTalkAnimations(string characterName, CharacterBehaviour talkingTo)
    {
        if (characterMap.ContainsKey(characterName))
        {
            characterMap[characterName].ToggleTalk(true, talkingTo);
        }
    }

    void StopTalkAnimations(string exceptCharacterName)
    {
        foreach (var characterName in characterMap.Keys)
        {
            if (characterName != exceptCharacterName)
            {
                characterMap[characterName].ToggleTalk(false);
            }
        }
    }

    public CharacterBehaviour GetTalkingCharacter()
    {
        foreach (CharacterBehaviour character in characterMap.Values)
        {
            if (character.talking)
            {
                return character;
            }
        }

        return null;
    }

    // Update is called once per frame
    IEnumerator GetStory()
    {
        audioClips = new List<AudioClip>();

        using (UnityWebRequest webRequest = UnityWebRequest.Get($"{serverURL}/story/getStory"))
        {
            yield return webRequest.SendWebRequest();
            story = JsonUtility.FromJson<StoryModel>(webRequest.downloadHandler.text);

            //No story found
            if (story == null)
            {
                Invoke("LoadStory", 2f);
                yield break;
            }

            //Initialize entire list with nulls so you can substitute at the right place as they come back asynchronously.
            for (int i = 0; i < story.scenario.Count; i++)
            {
                audioClips.Add(null);
            }

            for (int i = 0; i < story.scenario.Count; i++)
            {
                StartCoroutine(GetAudioClip(story.scenario[i].sound, i));
            }

            Invoke("CheckForSounds", 3f);
        }
    }

    IEnumerator GetAudioClip(string clipUrl, int pos)
    {
        using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip($"{serverURL}/audio/{clipUrl}", AudioType.OGGVORBIS))
        {
            yield return www.SendWebRequest();
            audioClips[pos] = DownloadHandlerAudioClip.GetContent(www);
        }
    }

    void CheckForSounds()
    {
        for (int i = 0; i < audioClips.Count; i++)
        {
            if (audioClips[i] == null)
            {
                Invoke("CheckForSounds", 3f);
                return;
            }
        }

        scenarioProgress = 0;
        requestor.text = "сценарий от: " + story.requestor_name;
        PlayScenario();
    }

    IEnumerator DeleteStory(string storyId)
    {
        using (UnityWebRequest webRequest = UnityWebRequest.Delete($"{serverURL}/delete/{storyId}"))
        {
            yield return webRequest.SendWebRequest();

            if (webRequest.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("Story deleted successfully");
            }
            else
            {
                Debug.LogError("Failed to delete story: " + webRequest.error);
            }
        }
    }
}

using System;
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
            Invoke("StartEndOfScenarioSequence", 1f);
        }
    }

    void StartEndOfScenarioSequence()
    {
        ShowLaterImageAndPlayClip();
        Invoke("HideLaterImageAndLoadNextScenario", 4f);
    }

    void ShowLaterImageAndPlayClip()
    {
        subtitles.text = "";
        laterImage.SetActive(true);
        dialogueSource.clip = laterClip;
        dialogueSource.Play();
    }

    void HideLaterImageAndLoadNextScenario()
    {
        StopTalkAnimations(null);
        dynamicCamera.ResetCamera();

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

        if (UnityEngine.Random.Range(0, 2) == 0)
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

    private void SetIddleTextIfNecessary()
    {
        if (story == null)
        {
            requestor.text = iddleText;
        }
    }

    // Update is called once per frame
    IEnumerator GetStory()
    {
        audioClips = new List<AudioClip>();

        using (UnityWebRequest webRequest = UnityWebRequest.Get($"{serverURL}/story/getStory"))
        {
            yield return webRequest.SendWebRequest();

            if (webRequest.result == UnityWebRequest.Result.ConnectionError || webRequest.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError("Server error: " + webRequest.error);
                SetIddleTextIfNecessary();
                StopTalkAnimations(null); 
                Invoke("LoadStory", 5f);
                yield break;
            }

            if (webRequest.responseCode == 404)
            {
                Debug.LogWarning("No story found, waiting to try again.");
                SetIddleTextIfNecessary();
                StopTalkAnimations(null); 
                Invoke("LoadStory", 5f);
                yield break;
            }

            if (webRequest.responseCode == 200)
            {
                try
                {
                    story = JsonUtility.FromJson<StoryModel>(webRequest.downloadHandler.text);
                    if (story == null)
                    {
                        Debug.LogWarning("Received empty story, waiting to try again.");
                        SetIddleTextIfNecessary();
                        StopTalkAnimations(null); 
                        Invoke("LoadStory", 5f);
                        yield break;
                    }

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
                catch (Exception e)
                {
                    Debug.LogError("JSON parse error: " + e.Message);
                    SetIddleTextIfNecessary();
                    StopTalkAnimations(null); 
                    Invoke("LoadStory", 5f);
                }
            }
            else
            {
                Debug.LogError("Unexpected server response code: " + webRequest.responseCode);
                SetIddleTextIfNecessary();
                StopTalkAnimations(null); 
                Invoke("LoadStory", 5f);
            }
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

        Invoke("StartPlayingScenario", 0.5f);
    }

    void StartPlayingScenario()
    {
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
